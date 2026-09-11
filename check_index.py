from __future__ import annotations

import json
from collections import Counter

from PIL import Image, UnidentifiedImageError

from build_index import file_hash
from catalog import load_catalog
from data_pipeline import Manifest, write_report
from faiss_io import read_index
from model_utils import OPENAI_VIT_B_16_SHA256
from settings import get_settings


def main() -> int:
    settings = get_settings()
    catalog = load_catalog(settings.absolute(settings.catalog_path))
    manifest = Manifest(settings.absolute(settings.manifest_path))
    report = write_report(manifest, catalog)
    counts = Counter(row["status"] for row in manifest.rows)
    problems = []
    if report["release_ready_objects"] < len(catalog):
        problems.append(
            f"dataset-ready classes {report['release_ready_objects']} < catalog {len(catalog)}"
        )
    accepted = [row for row in manifest.rows if row.get("status") == "accepted"]
    hashes = [row["sha256"] for row in accepted]
    original_rows = [
        row for row in accepted if row.get("is_augmented", "false").lower() != "true"
    ]
    phashes = [row["phash"] for row in original_rows]
    if len(hashes) != len(set(hashes)):
        problems.append("duplicate SHA-256 hashes remain in accepted images")
    if len(phashes) != len(set(phashes)):
        problems.append("duplicate perceptual hashes remain in curated original images")
    source_splits: dict[str, set[str]] = {}
    for row in accepted:
        group = row.get("source_group")
        if group:
            source_splits.setdefault(group, set()).add(row.get("split", ""))
    leaking_groups = [group for group, splits in source_splits.items() if len(splits) > 1]
    if leaking_groups:
        problems.append(f"source groups cross dataset splits: {len(leaking_groups)}")
    invalid_files = 0
    for row in accepted:
        path = settings.absolute(row["processed_path"])
        try:
            with Image.open(path) as image:
                image.verify()
        except (FileNotFoundError, OSError, UnidentifiedImageError):
            invalid_files += 1
    if invalid_files:
        problems.append(f"missing or corrupt processed images: {invalid_files}")
    valid_rights = {"open", "pending_purchase", "cleared", "rejected"}
    if any(row.get("rights_status") not in valid_rights for row in manifest.rows):
        problems.append("manifest contains an invalid rights_status")
    if (
        not settings.absolute(settings.index_path).exists()
        or not settings.absolute(settings.index_metadata_path).exists()
    ):
        problems.append("index artifacts are missing")
    else:
        metadata = json.loads(
            settings.absolute(settings.index_metadata_path).read_text(encoding="utf-8")
        )
        index = read_index(settings.absolute(settings.index_path))
        if index.ntotal != len(metadata.get("index_metadata", [])):
            problems.append("index and metadata vector counts differ")
        if metadata.get("catalog_sha256") != file_hash(
            settings.absolute(settings.catalog_path)
        ):
            problems.append("catalog version does not match index")
        if metadata.get("manifest_sha256") != file_hash(
            settings.absolute(settings.manifest_path)
        ):
            problems.append("manifest version does not match index")
        if metadata.get("model_checkpoint_sha256") != OPENAI_VIT_B_16_SHA256:
            problems.append("model checkpoint version does not match index")
        metrics = metadata.get("test_metrics", {})
        if metrics.get("top1_accuracy", 0) < 0.85:
            problems.append("top-1 accuracy is below 0.85")
        if metrics.get("macro_recall", 0) < 0.85:
            problems.append("macro recall is below 0.85")
        recalls = metrics.get("per_class_recall", {})
        ready_ids = metadata.get("ready_object_ids", [])
        if any(recalls.get(str(object_id), 0) < 0.70 for object_id in ready_ids):
            problems.append("a released class has recall below 0.70")
        if len(ready_ids) < 35:
            problems.append("fewer than 35 classes passed the release recall threshold")
        if metadata.get("calibration", {}).get("validation_false_accept_rate", 1) > 0.05:
            problems.append("false accept rate is above 0.05")
    print(
        json.dumps(
            {
                "catalog": len(catalog),
                "manifest": len(manifest.rows),
                "status": counts,
                "release_ready_objects": report["release_ready_objects"],
                "problems": problems,
            },
            ensure_ascii=False,
            indent=2,
            default=dict,
        )
    )
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
