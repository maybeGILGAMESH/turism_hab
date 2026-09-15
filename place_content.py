"""Extended travel content for catalog objects.

The recognition catalog (catalog/objects.json) is hashed into the FAISS metadata, so
editorial text lives separately in content/ and is joined by object_id at runtime.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

CONTENT_SCHEMA_VERSION = 1
MONTHS_GENITIVE = [
    "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
]
DIFFICULTY_LABELS = {
    "easy": "Лёгкий",
    "moderate": "Средний",
    "hard": "Сложный",
    "expedition": "Экспедиция",
}
ACCESSIBILITY_LABELS = {
    "step_free": "Доступно без ступеней",
    "partial": "Частично доступно",
    "limited": "Ограниченно доступно",
    "not_adapted": "Не приспособлено",
}
PROFILE_LABELS = {
    "urban": "Городская прогулка",
    "regional": "Поездка на день",
    "remote": "Удалённый объект",
}
# Volatile facts must not be frozen into the knowledge base: prices and opening hours.
VOLATILE_PATTERN = re.compile(r"\d\s*(?:руб|₽)|₽|\b\d{1,2}[:.]\d{2}\s*[-–—]\s*\d{1,2}[:.]\d{2}\b", re.I)

Difficulty = Literal["easy", "moderate", "hard", "expedition"]
Accessibility = Literal["step_free", "partial", "limited", "not_adapted"]
TripProfile = Literal["urban", "regional", "remote"]


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3)
    url: HttpUrl
    kind: Literal["official", "reference"] = "official"

    @field_validator("url")
    @classmethod
    def https_only(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https":
            raise ValueError("source URLs must use https")
        return value


class VisitMinutes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min: int = Field(ge=10, le=60 * 24 * 14)
    max: int = Field(ge=10, le=60 * 24 * 14)

    @model_validator(mode="after")
    def ordered(self) -> VisitMinutes:
        if self.min > self.max:
            raise ValueError("visit_minutes.min must not exceed max")
        return self


class Packing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summer: list[str] = Field(default_factory=list)
    winter: list[str] = Field(default_factory=list)
    offseason: list[str] = Field(default_factory=list)


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    packing: Packing
    safety: list[str] = Field(default_factory=list)
    etiquette: list[str] = Field(default_factory=list)


class PlaceContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object_id: int = Field(ge=1)
    aliases: list[str] = Field(default_factory=list)
    short_description: str = Field(min_length=40, max_length=240)
    full_description: str = Field(min_length=120)
    history: str = Field(min_length=60)
    highlights: list[str] = Field(min_length=2)
    visit_minutes: VisitMinutes
    best_months: list[int] = Field(min_length=1)
    seasonal_notes: str = Field(min_length=20)
    difficulty: Difficulty
    accessibility: Accessibility
    trip_profile: TripProfile
    transport: str = Field(min_length=30)
    family_tips: str = Field(min_length=20)
    reduced_mobility_tips: str = Field(min_length=20)
    profiles: list[str] = Field(min_length=1)
    packing: Packing = Field(default_factory=Packing)
    safety: list[str] = Field(default_factory=list)
    etiquette: list[str] = Field(default_factory=list)
    practical_tips: list[str] = Field(min_length=1)
    sources: list[Source] = Field(min_length=1)
    verified_at: date
    review_status: Literal["source_checked", "needs_editor_review"]

    @field_validator("best_months")
    @classmethod
    def valid_months(cls, value: list[int]) -> list[int]:
        if any(month < 1 or month > 12 for month in value) or len(set(value)) != len(value):
            raise ValueError("best_months must contain unique months 1..12")
        return sorted(value)

    @field_validator("verified_at")
    @classmethod
    def not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("verified_at cannot be in the future")
        return value

    @model_validator(mode="after")
    def no_volatile_facts(self) -> PlaceContent:
        texts = [
            self.short_description, self.full_description, self.history, self.seasonal_notes,
            self.transport, self.family_tips, self.reduced_mobility_tips,
            *self.highlights, *self.practical_tips, *self.safety, *self.etiquette,
        ]
        for text in texts:
            if VOLATILE_PATTERN.search(text):
                raise ValueError(
                    f"object {self.object_id}: prices and opening hours belong to official sources: {text!r}"
                )
        return self


class KnowledgeBase(BaseModel):
    version: str
    sha256: str
    places: dict[int, dict[str, object]]


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def content_files(content_dir: Path) -> list[Path]:
    return [content_dir / "profiles.json", *sorted((content_dir / "places").glob("*.json"))]


def content_sha256(content_dir: Path) -> str:
    digest = hashlib.sha256(f"schema:{CONTENT_SCHEMA_VERSION}\n".encode())
    for path in content_files(content_dir):
        digest.update(path.relative_to(content_dir).as_posix().encode() + b"\n")
        # Normalise line endings so a Windows checkout produces the same version.
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def months_label(months: list[int]) -> str:
    if len(months) == 12:
        return "круглый год"
    ranges: list[tuple[int, int]] = []
    for month in sorted(months):
        if ranges and month == ranges[-1][1] + 1:
            ranges[-1] = (ranges[-1][0], month)
        else:
            ranges.append((month, month))
    # December-January wrap-around.
    if len(ranges) > 1 and ranges[0][0] == 1 and ranges[-1][1] == 12:
        ranges = [(ranges[-1][0], ranges[0][1]), *ranges[1:-1]]
    parts = [
        MONTHS_GENITIVE[start - 1] if start == end
        else f"{MONTHS_GENITIVE[start - 1]}–{MONTHS_GENITIVE[end - 1]}"
        for start, end in ranges
    ]
    return ", ".join(parts)


def minutes_label(low: int, high: int) -> str:
    def one(value: int) -> str:
        if value < 60:
            return f"{value} мин"
        if value < 60 * 24:
            hours = value / 60
            return f"{hours:.1f}".rstrip("0").rstrip(".").replace(".", ",") + " ч"
        days = value / (60 * 24)
        return f"{days:.1f}".rstrip("0").rstrip(".").replace(".", ",") + " дн"

    return one(low) if low == high else f"{one(low)} – {one(high)}"


def seasons(months: list[int]) -> list[str]:
    names = {"winter": {12, 1, 2}, "spring": {3, 4, 5}, "summer": {6, 7, 8}, "autumn": {9, 10, 11}}
    return [name for name, values in names.items() if values & set(months)]


def _merge_unique(*groups: list[str]) -> list[str]:
    result: list[str] = []
    for group in groups:
        for item in group:
            if item not in result:
                result.append(item)
    return result


def load_content(content_dir: Path, catalog_ids: set[int] | None = None) -> dict[int, dict[str, object]]:
    """Validate all content files and return resolved cards keyed by object_id."""
    profiles = {
        name: Profile.model_validate(value)
        for name, value in dict(_read_json(content_dir / "profiles.json")).items()
    }
    places: dict[int, PlaceContent] = {}
    for path in sorted((content_dir / "places").glob("*.json")):
        for raw in list(_read_json(path)):
            place = PlaceContent.model_validate(raw)
            if place.object_id in places:
                raise ValueError(f"duplicate content for object_id {place.object_id} in {path.name}")
            unknown = set(place.profiles) - profiles.keys()
            if unknown:
                raise ValueError(f"object {place.object_id}: unknown profiles {sorted(unknown)}")
            places[place.object_id] = place
    if catalog_ids is not None:
        missing = catalog_ids - places.keys()
        orphan = places.keys() - catalog_ids
        if missing or orphan:
            raise ValueError(f"content/catalog mismatch: missing={sorted(missing)} orphan={sorted(orphan)}")

    resolved: dict[int, dict[str, object]] = {}
    for object_id, place in places.items():
        used = [profiles[name] for name in place.profiles]
        card = place.model_dump(mode="json", exclude={"profiles"})
        card["packing"] = {
            season: _merge_unique(*(getattr(p.packing, season) for p in used), getattr(place.packing, season))
            for season in ("summer", "winter", "offseason")
        }
        card["safety"] = _merge_unique(place.safety, *(p.safety for p in used))
        card["etiquette"] = _merge_unique(place.etiquette, *(p.etiquette for p in used))
        card["best_months_label"] = months_label(place.best_months)
        card["seasons"] = seasons(place.best_months)
        card["visit_label"] = minutes_label(place.visit_minutes.min, place.visit_minutes.max)
        card["difficulty_label"] = DIFFICULTY_LABELS[place.difficulty]
        card["accessibility_label"] = ACCESSIBILITY_LABELS[place.accessibility]
        card["trip_profile_label"] = PROFILE_LABELS[place.trip_profile]
        resolved[object_id] = card
    return resolved


SUMMARY_FIELDS = (
    "short_description", "best_months", "best_months_label", "seasons", "visit_minutes",
    "visit_label", "difficulty", "difficulty_label", "accessibility", "accessibility_label",
    "trip_profile", "trip_profile_label",
)


def summary(card: dict[str, object] | None) -> dict[str, object]:
    return {key: card.get(key) for key in SUMMARY_FIELDS} if card else {}


@lru_cache(maxsize=4)
def cached_content(content_dir: str, version: str) -> dict[int, dict[str, object]]:
    del version  # part of the cache key only
    return load_content(Path(content_dir))
