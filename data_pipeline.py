from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import logging
import math
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import imagehash
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError
from tqdm import tqdm

from catalog import Attraction, load_catalog
from model_utils import create_clip_model
from settings import ROOT, get_settings

LOGGER = logging.getLogger("khab-data")
MANIFEST_LOCK = threading.Lock()
USER_AGENT = "DiscoverKhabarovskKraiDataset/2.0 (local research; contact: dataset@khab.local)"
MANIFEST_FIELDS = [
    "object_id",
    "object_name",
    "source_provider",
    "source_page_url",
    "image_url",
    "author",
    "license",
    "rights_holder",
    "rights_status",
    "retrieved_at",
    "sha256",
    "phash",
    "width",
    "height",
    "mime_type",
    "raw_path",
    "processed_path",
    "source_group",
    "is_augmented",
    "parent_sha256",
    "augmentation",
    "split",
    "status",
    "rejection_reason",
]
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
NEGATIVE_QUERIES = [
    "Москва Красная площадь турист фото",
    "Санкт Петербург достопримечательности фото",
    "Кавказ горы турист фото",
    "Алтай озеро турист фото",
    "Владивосток достопримечательности фото",
    "городская улица Россия фото",
    "лес река пейзаж фото",
    "случайное здание Россия фото",
]


@dataclass(slots=True)
class ImageCandidate:
    provider: str
    image_url: str
    source_page_url: str
    author: str = ""
    license: str = "unknown"
    rights_holder: str = ""
    rights_status: str = "pending_purchase"


class Manifest:
    def __init__(self, path: Path):
        self.path = path
        self.rows: list[dict[str, str]] = []
        if path.exists():
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                self.rows = list(csv.DictReader(handle))
            for row in self.rows:
                if not row.get("source_provider"):
                    row["source_provider"] = (
                        "commons" if "wikimedia.org" in row.get("image_url", "") else "bing"
                    )

    @property
    def known_urls(self) -> set[str]:
        return {row["image_url"] for row in self.rows}

    @property
    def known_hashes(self) -> set[str]:
        return {row["sha256"] for row in self.rows if row.get("sha256")}

    @property
    def known_phashes(self) -> set[str]:
        return {
            row["phash"]
            for row in self.rows
            if row.get("phash") and row.get("status") == "accepted"
        }

    def add(self, row: dict[str, object]) -> None:
        self.rows.append({field: str(row.get(field, "")) for field in MANIFEST_FIELDS})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
            writer.writeheader()
            writer.writerows(self.rows)
        temp.replace(self.path)


class CommonsProvider:
    endpoint = "https://commons.wikimedia.org/w/api.php"

    def __init__(self, session: requests.Session):
        self.session = session

    def search(self, query: str, limit: int) -> list[ImageCandidate]:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}",
            "gsrnamespace": 6,
            "gsrlimit": min(limit, 50),
            "prop": "imageinfo",
            "iiprop": "url|mime|extmetadata",
            "format": "json",
            "formatversion": 2,
        }
        response = self.session.get(self.endpoint, params=params, timeout=30)
        response.raise_for_status()
        candidates: list[ImageCandidate] = []
        for page in response.json().get("query", {}).get("pages", []):
            info = (page.get("imageinfo") or [{}])[0]
            if info.get("mime") not in ALLOWED_MIME or not info.get("url"):
                continue
            metadata = info.get("extmetadata", {})
            author = _plain(metadata.get("Artist", {}).get("value", ""))
            license_name = metadata.get("LicenseShortName", {}).get("value", "unknown")
            canonical = (
                info.get("descriptionurl")
                or f"https://commons.wikimedia.org/?curid={page.get('pageid')}"
            )
            candidates.append(
                ImageCandidate(
                    provider="commons",
                    image_url=info["url"],
                    source_page_url=canonical,
                    author=author,
                    license=license_name,
                    rights_holder=author,
                    rights_status="open" if license_name != "unknown" else "pending_purchase",
                )
            )
        return candidates


class BingProvider:
    endpoint = "https://www.bing.com/images/search"

    def __init__(self, session: requests.Session):
        self.session = session

    def search(self, query: str, limit: int) -> list[ImageCandidate]:
        result: list[ImageCandidate] = []
        seen: set[str] = set()
        for first in range(1, limit + 1, 35):
            response = self.session.get(
                self.endpoint,
                params={
                    "q": query,
                    "form": "HDRSC2",
                    "first": first,
                    "count": min(35, limit - len(result)),
                    "tsc": "ImageBasicHover",
                },
                timeout=30,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for anchor in soup.select("a.iusc"):
                raw = anchor.get("m")
                if not raw:
                    continue
                try:
                    payload = json.loads(html.unescape(raw))
                except json.JSONDecodeError:
                    continue
                image_url = payload.get("murl", "")
                source_url = payload.get("purl", "")
                if not image_url.startswith(("http://", "https://")) or image_url in seen:
                    continue
                seen.add(image_url)
                result.append(
                    ImageCandidate(
                        provider="bing",
                        image_url=image_url,
                        source_page_url=source_url,
                        rights_holder=urlparse(source_url).netloc,
                        rights_status="pending_purchase",
                    )
                )
                if len(result) >= limit:
                    return result
            if not soup.select("a.iusc"):
                break
        return result


def _plain(value: str) -> str:
    return BeautifulSoup(value, "html.parser").get_text(" ", strip=True)


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁ]+", "-", value).strip("-")
    return normalized[:80] or "object"


def _extension(mime: str) -> str:
    return {"image/png": ".png", "image/webp": ".webp"}.get(mime, ".jpg")


def fetch_candidate(
    session: requests.Session,
    candidate: ImageCandidate,
    attraction: Attraction | None,
    manifest: Manifest,
    min_side: int,
) -> bool:
    object_id = attraction.id if attraction else 0
    object_name = attraction.name if attraction else "negative"
    base = {
        **asdict(candidate),
        "object_id": object_id,
        "object_name": object_name,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "status": "rejected",
    }
    try:
        response = session.get(candidate.image_url, timeout=(7, 15), stream=True)
        response.raise_for_status()
        mime = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
        if mime and mime not in ALLOWED_MIME:
            raise ValueError(f"unsupported MIME type: {mime}")
        payload = response.content
        if len(payload) > 25 * 1024 * 1024:
            raise ValueError("file exceeds 25 MB")
        with Image.open(io.BytesIO(payload)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(payload)) as opened:
            detected_mime = Image.MIME.get(opened.format, "image/jpeg")
            image = ImageOps.exif_transpose(opened).convert("RGB")
        width, height = image.size
        if min(width, height) < min_side:
            raise ValueError(f"image too small: {width}x{height}")
        digest = hashlib.sha256(payload).hexdigest()
        perceptual = str(imagehash.phash(image))
        with MANIFEST_LOCK:
            if digest in manifest.known_hashes:
                raise ValueError("duplicate sha256")
            if perceptual in manifest.known_phashes:
                raise ValueError("duplicate perceptual hash")

            raw_dir = ROOT / "dataset" / "raw" / f"{object_id:03d}"
            processed_dir = ROOT / "dataset" / "processed" / f"{object_id:03d}"
            raw_dir.mkdir(parents=True, exist_ok=True)
            processed_dir.mkdir(parents=True, exist_ok=True)
            raw_path = raw_dir / f"{digest}{_extension(mime)}"
            processed_path = processed_dir / f"{digest}.jpg"
            raw_path.write_bytes(payload)
            image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
            image.save(processed_path, "JPEG", quality=92, optimize=True)
            manifest.add(
                {
                    **base,
                    "sha256": digest,
                    "phash": perceptual,
                    "width": width,
                    "height": height,
                    "mime_type": mime or detected_mime,
                    "source_provider": candidate.provider,
                    "raw_path": raw_path.relative_to(ROOT).as_posix(),
                    "processed_path": processed_path.relative_to(ROOT).as_posix(),
                    "status": "accepted",
                    "rejection_reason": "",
                }
            )
        return True
    except (requests.RequestException, UnidentifiedImageError, OSError, ValueError) as error:
        with MANIFEST_LOCK:
            manifest.add(
                {
                    **base,
                    "source_provider": candidate.provider,
                    "rejection_reason": str(error)[:300],
                }
            )
        return False


def fetch_batch(
    session: requests.Session,
    candidates: list[ImageCandidate],
    attraction: Attraction | None,
    manifest: Manifest,
    min_side: int,
    workers: int,
) -> list[bool]:
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="image-download") as pool:
        return list(
            pool.map(
                lambda candidate: fetch_candidate(
                    session, candidate, attraction, manifest, min_side
                ),
                candidates,
            )
        )


def assign_splits(manifest: Manifest) -> None:
    accepted_by_object: dict[int, dict[str, list[dict[str, str]]]] = {}
    for row in manifest.rows:
        row["split"] = ""
        if row.get("status") == "accepted":
            group = row.get("source_group") or row.get("sha256") or row["image_url"]
            accepted_by_object.setdefault(int(row["object_id"]), {}).setdefault(
                group, []
            ).append(row)
    for object_id, grouped_rows in accepted_by_object.items():
        groups = sorted(
            grouped_rows,
            key=lambda group: hashlib.sha256(f"{object_id}|{group}".encode()).hexdigest(),
        )
        count = len(groups)
        if object_id == 0:
            for rows in grouped_rows.values():
                for row in rows:
                    row["split"] = "negative"
            continue
        if count >= 16:
            validation = max(3, math.floor(count * 0.15))
            test = max(3, math.floor(count * 0.15))
        elif count >= 4:
            validation, test = 1, 1
        elif count >= 2:
            validation, test = 0, 1
        else:
            validation, test = 0, 0
        for index, group in enumerate(groups):
            split = (
                "validation"
                if index < validation
                else "test"
                if index < validation + test
                else "index"
            )
            for row in grouped_rows[group]:
                row["split"] = split


def collect(args: argparse.Namespace) -> None:
    settings = get_settings()
    attractions = load_catalog(settings.absolute(settings.catalog_path))
    manifest = Manifest(settings.absolute(settings.manifest_path))
    session = requests.Session()
    session.headers.update(
        {"User-Agent": USER_AGENT, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}
    )
    providers = {"commons": CommonsProvider(session), "bing": BingProvider(session)}
    selected = [providers[name] for name in args.providers.split(",") if name in providers]
    if not selected:
        raise SystemExit("No valid providers selected")
    known_urls = manifest.known_urls

    for attraction in attractions:
        accepted = sum(
            1
            for row in manifest.rows
            if row.get("status") == "accepted" and int(row["object_id"]) == attraction.id
        )
        if accepted >= args.target:
            continue
        queries = attraction.search_queries or [f"{attraction.name} Хабаровский край"]
        progress = tqdm(
            total=args.target, initial=accepted, desc=f"{attraction.id:02d} {attraction.name[:28]}"
        )
        for query in queries:
            for provider in selected:
                try:
                    candidates = provider.search(query, args.candidates)
                except requests.RequestException as error:
                    LOGGER.warning(
                        "%s search failed for %s: %s", provider.__class__.__name__, query, error
                    )
                    continue
                pending = []
                for candidate in candidates:
                    if candidate.image_url not in known_urls:
                        known_urls.add(candidate.image_url)
                        pending.append(candidate)
                while pending and accepted < args.target:
                    remaining = args.target - accepted
                    batch, pending = pending[:remaining], pending[remaining:]
                    results = fetch_batch(
                        session,
                        batch,
                        attraction,
                        manifest,
                        args.min_side,
                        args.workers,
                    )
                    added = sum(results)
                    accepted += added
                    progress.update(added)
                    if args.delay:
                        time.sleep(args.delay)
                manifest.save()
                if accepted >= args.target:
                    break
            if accepted >= args.target:
                break
        progress.close()

    negative_count = sum(
        1 for row in manifest.rows if row.get("status") == "accepted" and row["object_id"] == "0"
    )
    for query in NEGATIVE_QUERIES:
        if negative_count >= args.negatives:
            break
        for provider in selected:
            try:
                candidates = provider.search(query, args.candidates)
            except requests.RequestException:
                continue
            pending = []
            for candidate in candidates:
                if candidate.image_url not in known_urls:
                    known_urls.add(candidate.image_url)
                    pending.append(candidate)
            while pending and negative_count < args.negatives:
                remaining = args.negatives - negative_count
                batch, pending = pending[:remaining], pending[remaining:]
                results = fetch_batch(session, batch, None, manifest, args.min_side, args.workers)
                negative_count += sum(results)
                if args.delay:
                    time.sleep(args.delay)
            if negative_count >= args.negatives:
                break
    assign_splits(manifest)
    manifest.save()
    write_report(manifest, attractions)


def collect_seed_urls(seed_path: Path, min_side: int, workers: int) -> int:
    """Download a curated URL list without executing code from result pages."""
    settings = get_settings()
    attractions = {
        item.id: item for item in load_catalog(settings.absolute(settings.catalog_path))
    }
    manifest = Manifest(settings.absolute(settings.manifest_path))
    known_urls = manifest.known_urls
    with seed_path.open("r", encoding="utf-8-sig", newline="") as handle:
        seeds = list(csv.DictReader(handle))
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "image/*,*/*;q=0.8"})
    jobs: list[tuple[ImageCandidate, Attraction | None]] = []
    for row in seeds:
        object_id = int(row["object_id"])
        attraction = attractions.get(object_id) if object_id else None
        if object_id and attraction is None:
            raise ValueError(f"Unknown object_id in seed list: {object_id}")
        image_url = row["image_url"].strip()
        if not image_url.startswith(("http://", "https://")) or image_url in known_urls:
            continue
        known_urls.add(image_url)
        jobs.append(
            (
                ImageCandidate(
                    provider="curated_url",
                    image_url=image_url,
                    source_page_url=row.get("source_page_url", "").strip() or image_url,
                    author=row.get("author", "").strip(),
                    license=row.get("license", "unknown").strip() or "unknown",
                    rights_holder=row.get("rights_holder", "").strip(),
                    rights_status=row.get("rights_status", "pending_purchase").strip()
                    or "pending_purchase",
                ),
                attraction,
            )
        )
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="seed-download") as pool:
        results = list(
            pool.map(
                lambda job: fetch_candidate(session, job[0], job[1], manifest, min_side),
                jobs,
            )
        )
    assign_splits(manifest)
    manifest.save()
    write_report(manifest, list(attractions.values()))
    return sum(results)


def write_report(manifest: Manifest, attractions: list[Attraction]) -> dict[str, object]:
    stats: list[dict[str, object]] = []
    for attraction in attractions:
        rows = [
            row
            for row in manifest.rows
            if row.get("status") == "accepted" and int(row["object_id"]) == attraction.id
        ]
        counts = {
            split: sum(row.get("split") == split for row in rows)
            for split in ("index", "validation", "test")
        }
        original_count = sum(row.get("is_augmented", "false").lower() != "true" for row in rows)
        stats.append(
            {
                "id": attraction.id,
                "name": attraction.name,
                "accepted": len(rows),
                "originals": original_count,
                "augmented": len(rows) - original_count,
                **counts,
                # Curated small-data profile: augmentations are allowed only in
                # index, while test remains an independent original image.
                "release_ready": counts["index"] >= 8 and counts["test"] >= 1,
            }
        )
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "catalog_objects": len(attractions),
        "release_ready_objects": sum(bool(item["release_ready"]) for item in stats),
        "negative_images": sum(
            row.get("status") == "accepted" and row["object_id"] == "0" for row in manifest.rows
        ),
        "objects": stats,
    }
    target = ROOT / "reports" / "dataset_report.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rights: dict[tuple[str, str, str, str], int] = {}
    for row in manifest.rows:
        if row.get("status") != "accepted":
            continue
        key = (
            row.get("rights_holder", ""),
            row.get("author", ""),
            row.get("license", "unknown"),
            row.get("rights_status", "pending_purchase"),
        )
        rights[key] = rights.get(key, 0) + 1
    rights_path = ROOT / "reports" / "rights_registry.csv"
    with rights_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["rights_holder", "author", "license", "rights_status", "files"],
        )
        writer.writeheader()
        for key, files in sorted(rights.items()):
            writer.writerow(
                {
                    "rights_holder": key[0],
                    "author": key[1],
                    "license": key[2],
                    "rights_status": key[3],
                    "files": files,
                }
            )
    return payload


def contact_sheets() -> None:
    settings = get_settings()
    attractions = load_catalog(settings.absolute(settings.catalog_path))
    manifest = Manifest(settings.absolute(settings.manifest_path))
    output = ROOT / "dataset" / "contact_sheets"
    output.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default()
    for font_path in (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ):
        if font_path.exists():
            font = ImageFont.truetype(str(font_path), 13)
            break
    for attraction in attractions:
        rows = [
            row
            for row in manifest.rows
            if row.get("status") == "accepted" and int(row["object_id"]) == attraction.id
        ]
        if not rows:
            continue
        cell_w, cell_h, columns = 240, 190, 4
        sheet = Image.new(
            "RGB", (cell_w * columns, cell_h * math.ceil(len(rows) / columns) + 45), "white"
        )
        draw = ImageDraw.Draw(sheet)
        draw.text(
            (10, 10),
            f"{attraction.id:02d} {attraction.name} ({len(rows)})",
            fill="black",
            font=font,
        )
        for index, row in enumerate(rows):
            image = Image.open(ROOT / row["processed_path"]).convert("RGB")
            image.thumbnail((cell_w - 10, cell_h - 30), Image.Resampling.LANCZOS)
            x = (index % columns) * cell_w + 5
            y = (index // columns) * cell_h + 45
            sheet.paste(image, (x, y))
            draw.text(
                (x, y + cell_h - 24),
                f"{index + 1} {row['sha256'][:8]} {row['split']} {row['rights_status']}",
                fill="black",
                font=font,
            )
        sheet.save(output / f"{attraction.id:03d}_{attraction.slug}.jpg", quality=88)


def clip_dedupe(threshold: float = 0.995, batch_size: int = 32) -> int:
    """Reject near-identical files using normalized CLIP embeddings.

    Deduplication is deliberately performed per object (including the negative class) so that
    visually similar but legitimately different landmarks are not collapsed across labels.
    """
    import os

    import numpy as np
    import torch

    settings = get_settings()
    manifest = Manifest(settings.absolute(settings.manifest_path))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_cache = settings.absolute(settings.model_cache_dir)
    model_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(model_cache))
    model, _, preprocess = create_clip_model(
        settings.model_name, settings.model_pretrained, model_cache
    )
    model = model.eval().to(device)
    rejected = 0
    object_ids = sorted(
        {int(row["object_id"]) for row in manifest.rows if row.get("status") == "accepted"}
    )
    for object_id in tqdm(object_ids, desc="CLIP dedupe classes"):
        rows = [
            row
            for row in manifest.rows
            if row.get("status") == "accepted" and int(row["object_id"]) == object_id
        ]
        if len(rows) < 2:
            continue
        vectors = []
        for start in range(0, len(rows), batch_size):
            batch = []
            for row in rows[start : start + batch_size]:
                with Image.open(ROOT / row["processed_path"]) as opened:
                    batch.append(preprocess(opened.convert("RGB")))
            with torch.inference_mode():
                features = model.encode_image(torch.stack(batch).to(device))
                features = features / features.norm(dim=-1, keepdim=True)
            vectors.append(features.cpu().numpy().astype("float32"))
        matrix = np.concatenate(vectors)
        kept: list[int] = []
        for index, row in enumerate(rows):
            duplicate_of = next(
                (
                    previous
                    for previous in kept
                    if float(matrix[index] @ matrix[previous]) >= threshold
                ),
                None,
            )
            if duplicate_of is None:
                kept.append(index)
            else:
                row["status"] = "rejected"
                row["split"] = ""
                row["rejection_reason"] = f"CLIP near-duplicate of {rows[duplicate_of]['sha256']}"
                rejected += 1
    assign_splits(manifest)
    manifest.save()
    return rejected


def export_cleared() -> None:
    import zipfile

    settings = get_settings()
    manifest = Manifest(settings.absolute(settings.manifest_path))
    output = ROOT / "dataset" / "exports" / "khabarovsk-cleared.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    cleared = [
        row
        for row in manifest.rows
        if row.get("status") == "accepted" and row.get("rights_status") in {"open", "cleared"}
    ]
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for row in cleared:
            path = ROOT / row["processed_path"]
            if path.exists():
                archive.write(path, row["processed_path"])
        content = io.StringIO()
        writer = csv.DictWriter(content, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(cleared)
        archive.writestr("manifest.csv", content.getvalue().encode("utf-8-sig"))


def apply_review(review_path: Path) -> int:
    settings = get_settings()
    manifest = Manifest(settings.absolute(settings.manifest_path))
    decisions = json.loads(review_path.read_text(encoding="utf-8"))
    rejected = 0
    for row in manifest.rows:
        reason = decisions.get(row.get("sha256", ""))
        if reason and row.get("status") == "accepted":
            row["status"] = "rejected"
            row["rights_status"] = "rejected"
            row["rejection_reason"] = f"manual review: {reason}"
            row["split"] = ""
            rejected += 1
    assign_splits(manifest)
    manifest.save()
    write_report(manifest, load_catalog(settings.absolute(settings.catalog_path)))
    return rejected


def main() -> None:
    parser = argparse.ArgumentParser(description="Khabarovsk Krai reproducible dataset pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    collect_parser = sub.add_parser("collect")
    collect_parser.add_argument("--providers", default="commons,bing")
    collect_parser.add_argument("--target", type=int, default=20)
    collect_parser.add_argument("--candidates", type=int, default=40)
    collect_parser.add_argument("--negatives", type=int, default=180)
    collect_parser.add_argument("--min-side", type=int, default=640)
    collect_parser.add_argument("--delay", type=float, default=0.15)
    collect_parser.add_argument("--workers", type=int, default=8)
    sub.add_parser("contact-sheets")
    dedupe_parser = sub.add_parser("clip-dedupe")
    dedupe_parser.add_argument("--threshold", type=float, default=0.995)
    dedupe_parser.add_argument("--batch-size", type=int, default=32)
    sub.add_parser("report")
    sub.add_parser("export-cleared")
    review_parser = sub.add_parser("apply-review")
    review_parser.add_argument(
        "--file", type=Path, default=ROOT / "dataset" / "review_decisions.json"
    )
    seeds_parser = sub.add_parser("collect-seeds")
    seeds_parser.add_argument(
        "--file", type=Path, default=ROOT / "dataset" / "seed_urls.csv"
    )
    seeds_parser.add_argument("--min-side", type=int, default=480)
    seeds_parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.command == "collect":
        collect(args)
    elif args.command == "contact-sheets":
        contact_sheets()
    elif args.command == "clip-dedupe":
        print(json.dumps({"rejected": clip_dedupe(args.threshold, args.batch_size)}))
    elif args.command == "report":
        settings = get_settings()
        manifest = Manifest(settings.absolute(settings.manifest_path))
        assign_splits(manifest)
        manifest.save()
        write_report(manifest, load_catalog(settings.absolute(settings.catalog_path)))
    elif args.command == "export-cleared":
        export_cleared()
    elif args.command == "apply-review":
        print(json.dumps({"rejected": apply_review(args.file)}, ensure_ascii=False))
    elif args.command == "collect-seeds":
        print(
            json.dumps(
                {"accepted": collect_seed_urls(args.file, args.min_side, args.workers)},
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
