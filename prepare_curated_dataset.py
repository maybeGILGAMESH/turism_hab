from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import imagehash
from PIL import Image, ImageEnhance, ImageOps, ImageStat, UnidentifiedImageError

from catalog import load_catalog
from data_pipeline import Manifest, write_report
from settings import ROOT, get_settings

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def portable_report_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def archive_current(paths: list[Path]) -> Path | None:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = ROOT / ".runtime" / "dataset-archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    for path in existing:
        destination = archive / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(destination))
    return archive


def choose_splits(rows: list[dict[str, str]]) -> dict[str, str]:
    ordered = sorted(
        rows,
        key=lambda row: hashlib.sha256(
            f"{row['object_id']}|{row['sha256']}".encode()
        ).hexdigest(),
    )
    result = {row["sha256"]: "index" for row in ordered}
    if len(ordered) >= 4:
        result[ordered[0]["sha256"]] = "validation"
        result[ordered[1]["sha256"]] = "test"
    elif len(ordered) >= 2:
        result[ordered[0]["sha256"]] = "test"
    return result


def augmented_image(image: Image.Image, variant: int) -> tuple[Image.Image, str]:
    """Return a deterministic, mild camera-like augmentation."""
    modes = (
        (-4.0, 0.03, 0.96, 1.04, 0.98),
        (4.0, 0.03, 1.04, 0.96, 1.02),
        (-2.0, 0.06, 0.92, 1.02, 1.04),
        (2.0, 0.06, 1.08, 0.98, 0.96),
        (0.0, 0.08, 0.96, 1.08, 1.00),
        (0.0, 0.04, 1.04, 0.92, 1.05),
    )
    angle, crop_ratio, brightness, contrast, color = modes[variant % len(modes)]
    width, height = image.size
    shift_seed = random.Random(variant * 1009 + width * 17 + height)
    crop_x = max(1, round(width * crop_ratio))
    crop_y = max(1, round(height * crop_ratio))
    left = shift_seed.randint(0, crop_x)
    top = shift_seed.randint(0, crop_y)
    right = width - (crop_x - left)
    bottom = height - (crop_y - top)
    result = image.crop((left, top, right, bottom)).resize(
        (width, height), Image.Resampling.LANCZOS
    )
    if angle:
        fill = tuple(round(value) for value in ImageStat.Stat(result).median)
        rotated = result.rotate(
            angle, Image.Resampling.BICUBIC, expand=True, fillcolor=fill
        )
        result = ImageOps.fit(rotated, (width, height), Image.Resampling.LANCZOS)
    result = ImageEnhance.Brightness(result).enhance(brightness)
    result = ImageEnhance.Contrast(result).enhance(contrast)
    result = ImageEnhance.Color(result).enhance(color)
    name = (
        f"rotate={angle:+.0f};crop={crop_ratio:.2f};brightness={brightness:.2f};"
        f"contrast={contrast:.2f};color={color:.2f}"
    )
    return result, name


def save_jpeg(image: Image.Image, target: Path, quality: int = 92) -> tuple[str, str]:
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, "JPEG", quality=quality, optimize=True)
    content = target.read_bytes()
    return sha256_bytes(content), str(imagehash.phash(image))


def prepare(source_root: Path, target_index: int = 12) -> dict[str, object]:
    settings = get_settings()
    source_root = source_root.resolve()
    source_manifest = source_root / "manifest.csv"
    if not source_manifest.is_file():
        raise FileNotFoundError(f"Curated manifest not found: {source_manifest}")
    catalog = {item.id: item for item in load_catalog(settings.absolute(settings.catalog_path))}
    with source_manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        supplied = list(csv.DictReader(handle))

    valid: list[dict[str, str]] = []
    missing = 0
    rejected = 0
    seen_sha: set[str] = set()
    for source_row in supplied:
        object_id = int(source_row["object_id"])
        if object_id not in catalog:
            raise ValueError(f"Unknown object_id {object_id}")
        source_path = (source_root / source_row["file"]).resolve()
        if source_root not in source_path.parents or not source_path.is_file():
            missing += 1
            continue
        if source_path.suffix.lower() not in IMAGE_SUFFIXES:
            rejected += 1
            continue
        content = source_path.read_bytes()
        digest = sha256_bytes(content)
        if digest in seen_sha:
            rejected += 1
            continue
        try:
            with Image.open(source_path) as opened:
                normalized = ImageOps.exif_transpose(opened).convert("RGB")
                normalized.load()
        except (OSError, UnidentifiedImageError):
            rejected += 1
            continue
        seen_sha.add(digest)
        valid.append({**source_row, "source_path": str(source_path), "sha256": digest})

    grouped: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in valid:
        grouped[int(row["object_id"])].append(row)
    missing_ids = sorted(set(catalog) - set(grouped))
    if missing_ids:
        raise RuntimeError(f"No valid curated images for object IDs: {missing_ids}")

    manifest_path = settings.absolute(settings.manifest_path)
    processed_root = ROOT / "dataset" / "processed"
    archive = archive_current(
        [
            manifest_path,
            processed_root,
            settings.absolute(settings.index_path),
            settings.absolute(settings.index_metadata_path),
            ROOT / "artifacts" / "embedding_cache.npz",
        ]
    )
    manifest = Manifest(manifest_path)

    for object_id, source_rows in sorted(grouped.items()):
        splits = choose_splits(source_rows)
        index_parents: list[tuple[dict[str, str], Path]] = []
        for source_row in sorted(source_rows, key=lambda row: row["file"]):
            source_path = Path(source_row["source_path"])
            with Image.open(source_path) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB")
                width, height = image.size
                original_sha = source_row["sha256"]
                target = processed_root / f"{object_id:03d}" / f"original-{original_sha}.jpg"
                processed_sha, phash = save_jpeg(image, target)
            split = splits[original_sha]
            common = {
                "object_id": object_id,
                "object_name": catalog[object_id].name,
                "source_provider": "curated_manual_yandex",
                "source_page_url": source_row.get("image_url", ""),
                "image_url": source_row.get("image_url", ""),
                "author": "",
                "license": "unknown",
                "rights_holder": "",
                "rights_status": "pending_purchase",
                "retrieved_at": datetime.now(UTC).isoformat(),
                "sha256": processed_sha,
                "phash": phash,
                "width": width,
                "height": height,
                "mime_type": "image/jpeg",
                "raw_path": source_path.relative_to(ROOT).as_posix(),
                "processed_path": target.relative_to(ROOT).as_posix(),
                "source_group": original_sha,
                "is_augmented": "false",
                "parent_sha256": "",
                "augmentation": "",
                "split": split,
                "status": "accepted",
                "rejection_reason": "",
            }
            manifest.add(common)
            if split == "index":
                index_parents.append((common, source_path))

        index_count = len(index_parents)
        variant = 0
        while index_count < target_index:
            parent, source_path = index_parents[variant % len(index_parents)]
            with Image.open(source_path) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB")
                generated, description = augmented_image(image, variant)
                target = (
                    processed_root
                    / f"{object_id:03d}"
                    / f"aug-{parent['source_group'][:12]}-{variant:02d}.jpg"
                )
                generated_sha, generated_phash = save_jpeg(
                    generated, target, quality=88 + (variant % 3) * 2
                )
                width, height = generated.size
            manifest.add(
                {
                    **parent,
                    "sha256": generated_sha,
                    "phash": generated_phash,
                    "width": width,
                    "height": height,
                    "raw_path": parent["raw_path"],
                    "processed_path": target.relative_to(ROOT).as_posix(),
                    "is_augmented": "true",
                    "parent_sha256": parent["sha256"],
                    "augmentation": description,
                    "split": "index",
                }
            )
            variant += 1
            index_count += 1

    manifest.save()
    dataset_report = write_report(manifest, list(catalog.values()))
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_root": portable_report_path(source_root),
        "supplied_manifest_rows": len(supplied),
        "missing_source_files": missing,
        "rejected_source_files": rejected,
        "accepted_originals": len(valid),
        "generated_augmentations": sum(
            row.get("is_augmented") == "true" for row in manifest.rows
        ),
        "catalog_objects": len(catalog),
        "target_index_per_object": target_index,
        "archive": portable_report_path(archive) if archive else None,
        "dataset_report": dataset_report,
    }
    report_path = ROOT / "reports" / "curated_import_report.json"
    report_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare the manually curated dataset")
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT
        / "dataset"
        / "datasets_clear"
        / "khabarovsk_tourism_44"
        / "work"
        / "khabarovsk_tourism_44",
    )
    parser.add_argument("--target-index", type=int, default=12)
    args = parser.parse_args()
    if args.target_index < 8:
        raise SystemExit("--target-index must be at least 8")
    print(json.dumps(prepare(args.source, args.target_index), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
