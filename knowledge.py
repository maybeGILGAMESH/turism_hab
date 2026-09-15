"""Local SQLite FTS5 knowledge base generated from catalog + content cards."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import threading
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from catalog import Attraction, load_catalog
from place_content import content_sha256, load_content
from settings import Settings

KB_SCHEMA_VERSION = 2
WORD_RE = re.compile(r"[a-zа-я0-9]+")
STOPWORDS = {
    "а", "без", "бы", "в", "вам", "вас", "во", "вот", "все", "всё", "где", "да", "для", "до",
    "его", "ее", "если", "есть", "же", "за", "и", "из", "или", "им", "их", "к", "как", "какая",
    "какие", "какой", "каком", "ко", "кто", "ли", "мне", "может", "можно", "мы", "на", "над",
    "надо", "не", "нет", "ни", "но", "ну", "о", "об", "от", "по", "под", "при", "про", "с", "со",
    "так", "там", "то", "ты", "у", "уже", "чем", "что", "чтобы", "это", "эта", "этот", "я",
    "расскажи", "расскажите", "подскажи", "подскажите", "пожалуйста", "хочу", "нужно", "стоит",
    "будет", "очень", "самый", "самое", "меня", "нам", "нас",
}
SECTION_TITLES = {
    "overview": "Описание",
    "history": "История и особенности",
    "season": "Сезон",
    "duration": "Продолжительность",
    "access": "Сложность и доступность",
    "transport": "Как добраться",
    "family": "Семьям с детьми",
    "packing": "Что взять с собой",
    "safety": "Безопасность",
    "etiquette": "Правила и этикет",
    "tips": "Практические советы",
}


def normalize(text: str) -> str:
    return text.lower().replace("ё", "е")


def stem(word: str) -> str:
    """Very small Russian-friendly stemmer: keep a stable prefix for prefix matching."""
    if len(word) <= 4 or word.isdigit():
        return word
    return word[: max(4, len(word) - 2)]


def words(text: str) -> list[str]:
    return WORD_RE.findall(normalize(text))


def query_stems(text: str) -> list[str]:
    result: list[str] = []
    for word in words(text):
        if word in STOPWORDS or (len(word) < 3 and not word.isdigit()):
            continue
        value = stem(word)
        if value not in result:
            result.append(value)
    return result


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _join(items: list[str]) -> str:
    return "; ".join(item.rstrip(".") for item in items) + "." if items else ""


def build_chunks(item: Attraction, card: dict[str, object]) -> list[tuple[str, str]]:
    packing = card["packing"]
    visit = card["visit_minutes"]
    sections = {
        "overview": f"{card['short_description']} {card['full_description']}",
        "history": f"{card['history']} Интересные особенности: {_join(card['highlights'])}",
        "season": f"Лучшие месяцы: {card['best_months_label']}. {card['seasonal_notes']}",
        "duration": (
            f"Рекомендуемая продолжительность посещения: {card['visit_label']} "
            f"(от {visit['min']} до {visit['max']} минут без учёта дороги). "
            f"Тип поездки: {card['trip_profile_label']}."
        ),
        "access": (
            f"Уровень сложности: {card['difficulty_label']}. Доступность: {card['accessibility_label']}. "
            f"{card['reduced_mobility_tips']}"
        ),
        "transport": (
            str(card["transport"])
            if str(card["transport"]).startswith("Адрес")
            else f"Адрес: {item.address}. {card['transport']}"
        ),
        "family": str(card["family_tips"]),
        "packing": (
            f"Летом: {_join(packing['summer'])} Зимой: {_join(packing['winter'])} "
            f"В межсезонье: {_join(packing['offseason'])}"
        ),
        "safety": _join(card["safety"]) or "Особых предупреждений в базе нет; соблюдайте общие правила безопасности.",
        "etiquette": _join(card["etiquette"]) or "Соблюдайте общие правила поведения в общественных местах.",
        "tips": _join(card["practical_tips"]),
    }
    return [(section, body) for section, body in sections.items() if body.strip()]


class KnowledgeBase:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.lock = threading.RLock()
        self.db_path = settings.absolute(settings.knowledge_db_path)
        self.meta_path = self.db_path.with_name(self.db_path.stem + ".meta.json")
        self.content_dir = settings.absolute(settings.content_dir)
        self.catalog: dict[int, Attraction] = {}
        self.cards: dict[int, dict[str, object]] = {}
        self.meta: dict[str, object] = {}
        self.error = ""

    @property
    def ready(self) -> bool:
        return bool(self.cards) and self.db_path.exists() and not self.error

    @property
    def version(self) -> str:
        return str(self.meta.get("version", ""))

    def _expected_version(self, catalog_path: Path) -> tuple[str, str, str]:
        content_hash = content_sha256(self.content_dir)
        catalog_hash = file_sha256(catalog_path)
        combined = hashlib.sha256(
            f"kb{KB_SCHEMA_VERSION}:{content_hash}:{catalog_hash}".encode()
        ).hexdigest()
        return f"kb{KB_SCHEMA_VERSION}-{combined[:12]}", content_hash, catalog_hash

    def ensure_ready(self, force: bool = False) -> None:
        with self.lock:
            try:
                catalog_path = self.settings.absolute(self.settings.catalog_path)
                version, content_hash, catalog_hash = self._expected_version(catalog_path)
                if not force and self.cards and self.meta.get("version") == version and self.db_path.exists():
                    return
                self.catalog = {item.id: item for item in load_catalog(catalog_path) if item.enabled}
                cards = load_content(self.content_dir)
                self.cards = {object_id: card for object_id, card in cards.items() if object_id in self.catalog}
                meta = self._read_meta()
                if (
                    force
                    or meta.get("version") != version
                    or not self.db_path.exists()
                    or file_sha256(self.db_path) != meta.get("db_sha256")
                ):
                    meta = self._build(version, content_hash, catalog_hash)
                self.meta = meta
                self.error = ""
            except Exception as error:  # surfaced through /health instead of crashing the API
                self.error = f"{type(error).__name__}: {error}"

    def _read_meta(self) -> dict[str, object]:
        try:
            return json.loads(self.meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _build(self, version: str, content_hash: str, catalog_hash: str) -> dict[str, object]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.db_path.with_name(f"{self.db_path.name}.tmp-{os.getpid()}")
        temp_path.unlink(missing_ok=True)
        connection = sqlite3.connect(temp_path)
        chunk_count = 0
        try:
            connection.executescript(
                """
                CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE places(object_id INTEGER PRIMARY KEY, name TEXT NOT NULL,
                                    municipality TEXT NOT NULL, card_json TEXT NOT NULL);
                CREATE VIRTUAL TABLE chunks USING fts5(
                    object_id UNINDEXED, section UNINDEXED, name, body,
                    tokenize = 'unicode61 remove_diacritics 2'
                );
                """
            )
            for object_id in sorted(self.cards):
                item, card = self.catalog[object_id], self.cards[object_id]
                connection.execute(
                    "INSERT INTO places VALUES (?, ?, ?, ?)",
                    (object_id, item.name, item.municipality, json.dumps(card, ensure_ascii=False, sort_keys=True)),
                )
                aliases = " ".join(card.get("aliases", []))
                for section, body in build_chunks(item, card):
                    connection.execute(
                        "INSERT INTO chunks(object_id, section, name, body) VALUES (?, ?, ?, ?)",
                        (object_id, section, f"{item.name} {aliases}", body),
                    )
                    chunk_count += 1
            meta = {
                "schema_version": KB_SCHEMA_VERSION,
                "version": version,
                "content_sha256": content_hash,
                "catalog_sha256": catalog_hash,
                "places": len(self.cards),
                "chunks": chunk_count,
                "missing_content_object_ids": sorted(set(self.catalog) - set(self.cards)),
            }
            connection.executemany("INSERT INTO meta VALUES (?, ?)", [(k, json.dumps(v)) for k, v in meta.items()])
            connection.commit()
        finally:
            connection.close()
        os.replace(temp_path, self.db_path)
        meta["built_at"] = datetime.now(UTC).isoformat()
        meta["db_sha256"] = file_sha256(self.db_path)
        self.meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return meta

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(f"{self.db_path.resolve().as_uri()}?mode=ro", uri=True)

    def chunks_for(self, object_ids: list[int], sections: list[str]) -> list[dict[str, object]]:
        if not object_ids or not sections:
            return []
        self.ensure_ready()
        result: list[dict[str, object]] = []
        with closing(self._connect()) as connection:
            for object_id in object_ids:
                for section in sections:
                    row = connection.execute(
                        "SELECT body FROM chunks WHERE object_id = ? AND section = ?", (object_id, section)
                    ).fetchone()
                    if row:
                        result.append(self._chunk(object_id, section, row[0]))
        return result

    def search(
        self, query: str, object_ids: list[int] | None = None, limit: int = 4
    ) -> list[dict[str, object]]:
        """BM25 search; a hit must cover most of the meaningful query terms to count."""
        stems = query_stems(query)
        if not stems:
            return []
        self.ensure_ready()
        match = " OR ".join(f'"{value}"*' for value in stems)
        sql = "SELECT object_id, section, name, body, bm25(chunks, 0, 0, 4.0, 1.0) FROM chunks WHERE chunks MATCH ?"
        params: list[object] = [match]
        if object_ids:
            sql += f" AND object_id IN ({','.join('?' * len(object_ids))})"
            params.extend(object_ids)
        sql += " ORDER BY bm25(chunks, 0, 0, 4.0, 1.0) LIMIT 40"
        required = 1 if len(stems) == 1 else max(2, math.ceil(len(stems) * 0.6))
        hits: list[dict[str, object]] = []
        with closing(self._connect()) as connection:
            for object_id, section, name, body, score in connection.execute(sql, params):
                haystack = words(f"{name} {body}")
                covered = sum(1 for value in stems if any(word.startswith(value) for word in haystack))
                if covered < required:
                    continue
                chunk = self._chunk(int(object_id), str(section), str(body))
                chunk["score"] = round(float(score), 4)
                chunk["covered_terms"] = covered
                hits.append(chunk)
                if len(hits) >= limit:
                    break
        return hits

    def _chunk(self, object_id: int, section: str, body: str) -> dict[str, object]:
        item = self.catalog.get(object_id)
        return {
            "object_id": object_id,
            "name": item.name if item else str(object_id),
            "municipality": item.municipality if item else "",
            "section": section,
            "section_title": SECTION_TITLES.get(section, section),
            "body": body,
        }
