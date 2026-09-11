from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import faiss
import numpy as np
import torch
from PIL import Image
from tqdm import tqdm

from catalog import load_catalog
from model_utils import create_clip_model
from settings import ROOT, get_settings


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_device(requested: str) -> str:
    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but is not available")
    return requested


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [row for row in csv.DictReader(handle) if row.get("status") == "accepted"]


def encode_images(
    model, preprocess, rows: list[dict[str, str]], device: str, batch_size: int
) -> np.ndarray:
    vectors: list[np.ndarray] = []
    for start in tqdm(range(0, len(rows), batch_size), desc="CLIP embeddings"):
        batch_rows = rows[start : start + batch_size]
        tensors = []
        for row in batch_rows:
            with Image.open(ROOT / row["processed_path"]) as image:
                tensors.append(preprocess(image.convert("RGB")))
        images = torch.stack(tensors).to(device)
        with torch.inference_mode():
            features = model.encode_image(images)
            features = features / features.norm(dim=-1, keepdim=True)
        vectors.append(features.cpu().numpy().astype("float32"))
    return np.concatenate(vectors) if vectors else np.empty((0, 512), dtype="float32")


def class_scores(
    index: faiss.Index, metadata: list[dict[str, object]], query: np.ndarray
) -> list[tuple[int, float]]:
    scores, positions = index.search(query.reshape(1, -1), index.ntotal)
    grouped: dict[int, list[float]] = defaultdict(list)
    for score, position in zip(scores[0], positions[0], strict=False):
        if position < 0:
            continue
        grouped[int(metadata[position]["object_id"])].append(float(score))
    ranked = []
    for object_id, values in grouped.items():
        values.sort(reverse=True)
        selected = np.asarray(values[: min(2, len(values))], dtype="float32")
        weights = np.exp(-0.5 * np.arange(len(selected), dtype="float32"))
        ranked.append((object_id, float(np.average(selected, weights=weights))))
    return sorted(ranked, key=lambda item: item[1], reverse=True)


def cross_validate_sources(
    rows: list[dict[str, str]], vectors: np.ndarray
) -> tuple[float, float, dict[str, object], dict[str, object]]:
    """Evaluate every original while excluding its source group from candidates."""
    labels = np.asarray([int(row["object_id"]) for row in rows])
    groups = np.asarray([row.get("source_group") or row["sha256"] for row in rows])
    original_positions = [
        index
        for index, row in enumerate(rows)
        if row.get("is_augmented", "false").lower() != "true"
    ]
    positives: list[tuple[bool, float, float]] = []
    impostor_scores: list[float] = []
    outcomes: list[tuple[int, bool, float, float]] = []
    for position in original_positions:
        candidate_mask = groups != groups[position]
        similarities = vectors[candidate_mask] @ vectors[position]
        candidate_labels = labels[candidate_mask]
        ranked: list[tuple[int, float]] = []
        for object_id in np.unique(candidate_labels):
            values = np.sort(similarities[candidate_labels == object_id])[-2:][::-1]
            weights = np.exp(-0.5 * np.arange(len(values), dtype="float32"))
            ranked.append((int(object_id), float(np.average(values, weights=weights))))
        ranked.sort(key=lambda item: item[1], reverse=True)
        expected = int(labels[position])
        predicted, score = ranked[0]
        margin = score - (ranked[1][1] if len(ranked) > 1 else 0.0)
        correct = predicted == expected
        positives.append((correct, score, margin))
        outcomes.append((expected, correct, score, margin))
        wrong = next((value for object_id, value in ranked if object_id != expected), None)
        if wrong is not None:
            impostor_scores.append(wrong)

    best = (0.25, 0.02, -1.0)
    for threshold in np.arange(0.20, 1.001, 0.01):
        far = float(np.mean([score >= threshold for score in impostor_scores]))
        if far > 0.05:
            continue
        for margin_threshold in np.arange(0.0, 0.151, 0.01):
            accepted_correct = sum(
                ok and score >= threshold and margin >= margin_threshold
                for ok, score, margin in positives
            )
            utility = accepted_correct / max(1, len(positives))
            if utility > best[2]:
                best = (float(threshold), float(margin_threshold), utility)

    class_total: dict[int, int] = defaultdict(int)
    class_correct: dict[int, int] = defaultdict(int)
    accepted_correct = 0
    for object_id, correct, score, margin in outcomes:
        class_total[object_id] += 1
        class_correct[object_id] += int(correct)
        accepted_correct += int(correct and score >= best[0] and margin >= best[1])
    recalls = {
        str(object_id): class_correct[object_id] / total
        for object_id, total in class_total.items()
    }
    calibration: dict[str, object] = {
        "validation_top1": float(np.mean([ok for ok, _, _ in positives])),
        "validation_accepted_correct": best[2],
        "validation_false_accept_rate": float(
            np.mean([score >= best[0] for score in impostor_scores])
        ),
        "false_accept_source": "leave_one_source_out_wrong_class_proxy",
        "explicit_negative_samples": 0,
        "impostor_proxy_samples": len(impostor_scores),
    }
    metrics: dict[str, object] = {
        "samples": len(outcomes),
        "top1_accuracy": sum(correct for _, correct, _, _ in outcomes)
        / max(1, len(outcomes)),
        "accepted_correct_rate": accepted_correct / max(1, len(outcomes)),
        "per_class_recall": recalls,
        "macro_recall": float(np.mean(list(recalls.values()))) if recalls else 0.0,
        "evaluation_method": "leave_one_source_group_out",
    }
    return best[0], best[1], calibration, metrics


def calibrate(
    index: faiss.Index,
    index_metadata: list[dict[str, object]],
    validation_rows: list[dict[str, str]],
    validation_vectors: np.ndarray,
    negative_rows: list[dict[str, str]],
    negative_vectors: np.ndarray,
) -> tuple[float, float, dict[str, object]]:
    positives: list[tuple[bool, float, float]] = []
    impostor_scores: list[float] = []
    for row, vector in zip(validation_rows, validation_vectors, strict=True):
        ranked = class_scores(index, index_metadata, vector)
        if not ranked:
            continue
        expected_id = int(row["object_id"])
        margin = ranked[0][1] - (ranked[1][1] if len(ranked) > 1 else 0.0)
        positives.append((ranked[0][0] == expected_id, ranked[0][1], margin))
        wrong = next((score for object_id, score in ranked if object_id != expected_id), None)
        if wrong is not None:
            impostor_scores.append(wrong)
    negative_scores = []
    for vector in negative_vectors:
        ranked = class_scores(index, index_metadata, vector)
        if ranked:
            negative_scores.append(ranked[0][1])

    # When the curated delivery contains no explicit unrelated photographs,
    # calibrate conservatively on the strongest wrong class for every
    # validation image. This is an honest proxy, not an unknown-image FAR.
    calibration_negatives = negative_scores or impostor_scores
    false_accept_source = (
        "explicit_negative_images" if negative_scores else "wrong_class_impostor_proxy"
    )
    best = (0.25, 0.02, -1.0)
    for threshold in np.arange(0.20, 1.001, 0.01):
        far = (
            float(np.mean([score >= threshold for score in calibration_negatives]))
            if calibration_negatives
            else 0.0
        )
        if far > 0.05:
            continue
        for margin_threshold in np.arange(0.0, 0.151, 0.01):
            accepted_correct = sum(
                ok and score >= threshold and margin >= margin_threshold
                for ok, score, margin in positives
            )
            utility = accepted_correct / max(1, len(positives))
            if utility > best[2]:
                best = (float(threshold), float(margin_threshold), utility)
    metrics = {
        "validation_top1": float(np.mean([ok for ok, _, _ in positives])) if positives else 0.0,
        "validation_accepted_correct": best[2],
        "validation_false_accept_rate": float(
            np.mean([score >= best[0] for score in calibration_negatives])
        )
        if calibration_negatives
        else 0.0,
        "false_accept_source": false_accept_source,
        "explicit_negative_samples": len(negative_scores),
        "impostor_proxy_samples": len(impostor_scores),
    }
    return best[0], best[1], metrics


def evaluate(
    index: faiss.Index,
    index_metadata: list[dict[str, object]],
    rows: list[dict[str, str]],
    vectors: np.ndarray,
    score_threshold: float,
    margin_threshold: float,
) -> dict[str, object]:
    class_total: dict[int, int] = defaultdict(int)
    class_correct: dict[int, int] = defaultdict(int)
    correct = accepted_correct = 0
    for row, vector in zip(rows, vectors, strict=True):
        object_id = int(row["object_id"])
        ranked = class_scores(index, index_metadata, vector)
        class_total[object_id] += 1
        if not ranked:
            continue
        is_correct = ranked[0][0] == object_id
        margin = ranked[0][1] - (ranked[1][1] if len(ranked) > 1 else 0.0)
        if is_correct:
            correct += 1
            class_correct[object_id] += 1
        if is_correct and ranked[0][1] >= score_threshold and margin >= margin_threshold:
            accepted_correct += 1
    recalls = {str(key): class_correct[key] / total for key, total in class_total.items()}
    return {
        "samples": len(rows),
        "top1_accuracy": correct / max(1, len(rows)),
        "accepted_correct_rate": accepted_correct / max(1, len(rows)),
        "per_class_recall": recalls,
        "macro_recall": float(np.mean(list(recalls.values()))) if recalls else 0.0,
    }


def build(device_requested: str = "auto", batch_size: int = 16) -> dict[str, object]:
    settings = get_settings()
    catalog_path = settings.absolute(settings.catalog_path)
    manifest_path = settings.absolute(settings.manifest_path)
    index_path = settings.absolute(settings.index_path)
    metadata_path = settings.absolute(settings.index_metadata_path)
    catalog = {item.id: item for item in load_catalog(catalog_path) if item.enabled}
    rows = load_manifest(manifest_path)
    split_counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        object_id = int(row["object_id"])
        if object_id > 0:
            split_counts[object_id][row["split"]] += 1
    eligible_ids = {
        object_id
        for object_id, counts in split_counts.items()
        if counts["index"] >= 8 and counts["test"] >= 1
    }
    catalog = {object_id: item for object_id, item in catalog.items() if object_id in eligible_ids}
    index_rows = [
        row for row in rows if row["split"] == "index" and int(row["object_id"]) in catalog
    ]
    validation_rows = [
        row for row in rows if row["split"] == "validation" and int(row["object_id"]) in catalog
    ]
    test_rows = [row for row in rows if row["split"] == "test" and int(row["object_id"]) in catalog]
    negative_rows = [row for row in rows if row["split"] == "negative"]
    if not index_rows:
        raise RuntimeError(
            "No class has at least 8 index and 1 independent test image"
        )

    device = resolve_device(device_requested)
    settings.absolute(settings.model_cache_dir).mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(settings.absolute(settings.model_cache_dir)))
    model, _, preprocess = create_clip_model(
        settings.model_name,
        settings.model_pretrained,
        settings.absolute(settings.model_cache_dir),
    )
    model = model.eval().to(device)
    object_rows = index_rows + validation_rows + test_rows
    all_rows = object_rows + negative_rows
    row_fingerprint = hashlib.sha256(
        "|".join(row["sha256"] for row in all_rows).encode()
    ).hexdigest()
    embedding_cache = index_path.parent / "embedding_cache.npz"
    all_vectors: np.ndarray
    if embedding_cache.exists():
        cached = np.load(embedding_cache)
        cached_fingerprint = str(cached["fingerprint"].item())
        cached_vectors = cached["vectors"]
        if cached_fingerprint == row_fingerprint and len(cached_vectors) == len(all_rows):
            all_vectors = cached_vectors.astype("float32", copy=False)
        else:
            all_vectors = encode_images(model, preprocess, all_rows, device, batch_size)
            np.savez_compressed(
                embedding_cache, fingerprint=row_fingerprint, vectors=all_vectors
            )
    else:
        all_vectors = encode_images(model, preprocess, all_rows, device, batch_size)
        np.savez_compressed(embedding_cache, fingerprint=row_fingerprint, vectors=all_vectors)
    object_vectors = all_vectors[: len(object_rows)]

    index = faiss.IndexFlatIP(object_vectors.shape[1])
    index.add(object_vectors)
    index_metadata = [
        {
            "object_id": int(row["object_id"]),
            "processed_path": row["processed_path"],
            "sha256": row["sha256"],
        }
        for row in object_rows
    ]
    score_threshold, margin_threshold, calibration, test_metrics = cross_validate_sources(
        object_rows, object_vectors
    )
    ready_ids = [
        int(key) for key, recall in test_metrics["per_class_recall"].items() if recall >= 0.70
    ]
    payload: dict[str, object] = {
        "schema_version": 2,
        "dataset_profile": "curated-small-v1",
        "evaluation_note": (
            "Metrics use leave-one-source-group-out cross-validation over every original. "
            "The evaluated original and all of its augmentations are excluded from its fold. "
            "The final serving index is then fitted on all curated images. Without explicit "
            "negative images, FAR is an impostor-class proxy."
        ),
        "created_at": datetime.now(UTC).isoformat(),
        "catalog_sha256": file_hash(catalog_path),
        "manifest_sha256": file_hash(manifest_path),
        "model_name": settings.model_name,
        "model_pretrained": settings.model_pretrained,
        "model_checkpoint_sha256": file_hash(
            settings.absolute(settings.model_cache_dir) / f"{settings.model_name}.pt"
        ),
        "embedding_dimension": int(object_vectors.shape[1]),
        "image_count": len(object_rows),
        "object_count": len({int(row["object_id"]) for row in object_rows}),
        "eligible_object_ids": sorted(eligible_ids),
        "ready_object_ids": sorted(ready_ids),
        "score_threshold": score_threshold,
        "margin_threshold": margin_threshold,
        "index_metadata": index_metadata,
        "calibration": calibration,
        "test_metrics": test_metrics,
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    # FAISS' Windows C++ file writer cannot open paths containing Cyrillic.
    # Write through the project runtime's ASCII junction, then atomically move it.
    faiss_temp_dir = Path(f"{ROOT.drive}\\turism_hab_runtime\\faiss-temp")
    faiss_temp_dir.mkdir(parents=True, exist_ok=True)
    temp_index = faiss_temp_dir / "index.tmp.faiss"
    temp_metadata = metadata_path.with_suffix(".tmp.json")
    faiss.write_index(index, str(temp_index))
    temp_metadata.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if index_path.exists():
        shutil.copy2(index_path, index_path.with_suffix(".bak.faiss"))
    if metadata_path.exists():
        shutil.copy2(metadata_path, metadata_path.with_suffix(".bak.json"))
    shutil.move(str(temp_index), str(index_path))
    temp_metadata.replace(metadata_path)
    (ROOT / "reports" / "quality_report.json").write_text(
        json.dumps(
            {
                "calibration": calibration,
                "test": test_metrics,
                "release_ready_objects": len(ready_ids),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Khabarovsk CLIP/FAISS index")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    result = build(args.device, args.batch_size)
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "index_metadata"},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
