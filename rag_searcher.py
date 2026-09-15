from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path
from threading import RLock

import faiss
import numpy as np
import torch
from PIL import Image

from catalog import Attraction, load_catalog
from faiss_io import read_index
from model_utils import OPENAI_VIT_B_16_SHA256, create_clip_model
from settings import Settings


class IndexNotReady(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class RAGSearcher:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.lock = RLock()
        self.catalog: dict[int, Attraction] = {}
        self.metadata: dict[str, object] = {}
        self.index: faiss.Index | None = None
        self.model = None
        self.preprocess = None
        self.device = "cpu"
        self.reason = "not loaded"
        self.reload()

    @property
    def ready(self) -> bool:
        return self.index is not None and bool(self.catalog) and not self.reason

    @property
    def quality_ready(self) -> bool:
        metrics = self.metadata.get("test_metrics", {})
        calibration = self.metadata.get("calibration", {})
        return (
            self.ready
            and float(metrics.get("top1_accuracy", 0)) >= 0.85
            and float(metrics.get("macro_recall", 0)) >= 0.85
            and float(calibration.get("validation_false_accept_rate", 1)) <= 0.05
            and len(self.metadata.get("ready_object_ids", [])) >= 35
        )

    def reload(self) -> None:
        with self.lock:
            self.catalog = {
                item.id: item
                for item in load_catalog(self.settings.absolute(self.settings.catalog_path))
                if item.enabled
            }
            index_path = self.settings.absolute(self.settings.index_path)
            metadata_path = self.settings.absolute(self.settings.index_metadata_path)
            if not index_path.exists() or not metadata_path.exists():
                self.index = None
                self.reason = "index artifacts are missing"
                return
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            catalog_hash = _sha256(self.settings.absolute(self.settings.catalog_path))
            manifest_path = self.settings.absolute(self.settings.manifest_path)
            manifest_hash = _sha256(manifest_path) if manifest_path.exists() else ""
            if (
                metadata.get("catalog_sha256") != catalog_hash
                or metadata.get("manifest_sha256") != manifest_hash
                or metadata.get("model_name") != self.settings.model_name
                or metadata.get("model_pretrained") != self.settings.model_pretrained
                or metadata.get("model_checkpoint_sha256") != OPENAI_VIT_B_16_SHA256
            ):
                self.index = None
                self.metadata = metadata
                self.reason = "catalog/manifest/model version does not match index"
                return
            index = read_index(index_path, self.settings.runtime_alias_dir)
            if index.ntotal != len(metadata.get("index_metadata", [])):
                self.index = None
                self.metadata = metadata
                self.reason = "index vector count does not match metadata"
                return
            self.index = index
            self.metadata = metadata
            self.reason = ""

    def _ensure_model(self) -> None:
        if self.model is not None:
            return
        requested = self.settings.device
        self.device = "cuda" if requested == "auto" and torch.cuda.is_available() else requested
        if self.device not in {"cpu", "cuda"}:
            self.device = "cpu"
        if self.device == "cuda" and not torch.cuda.is_available():
            self.device = "cpu"
        model_cache = self.settings.absolute(self.settings.model_cache_dir)
        model_cache.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HOME", str(model_cache))
        model, _, preprocess = create_clip_model(
            self.settings.model_name,
            self.settings.model_pretrained,
            model_cache,
        )
        self.model = model.eval().to(self.device)
        self.preprocess = preprocess

    def vectorize(self, image_path: Path) -> np.ndarray:
        self._ensure_model()
        with Image.open(image_path) as image:
            tensor = self.preprocess(image.convert("RGB")).unsqueeze(0).to(self.device)
        with torch.inference_mode():
            vector = self.model.encode_image(tensor)
            vector = vector / vector.norm(dim=-1, keepdim=True)
        return vector.cpu().numpy().astype("float32")[0]

    def search(self, image_path: Path, top_k: int = 5) -> dict[str, object]:
        with self.lock:
            if not self.ready or self.index is None:
                raise IndexNotReady(self.reason or "index is not ready")
            vector = self.vectorize(image_path)
            neighbors = self.index.ntotal
            scores, positions = self.index.search(vector.reshape(1, -1), neighbors)
            grouped: dict[int, list[float]] = defaultdict(list)
            index_metadata = self.metadata["index_metadata"]
            ready_ids = {int(value) for value in self.metadata.get("ready_object_ids", [])}
            for score, position in zip(scores[0], positions[0], strict=False):
                if position >= 0:
                    object_id = int(index_metadata[position]["object_id"])
                    if object_id in ready_ids:
                        grouped[object_id].append(float(score))
            candidates = []
            for object_id, values in grouped.items():
                values.sort(reverse=True)
                aggregate = float(np.mean(values[: min(2, len(values))]))
                item = self.catalog.get(object_id)
                if item:
                    candidates.append(
                        {"object_id": object_id, "score": aggregate, "name": item.name}
                    )
            candidates.sort(key=lambda item: item["score"], reverse=True)
            candidates = candidates[:top_k]
            best_score = candidates[0]["score"] if candidates else 0.0
            margin = best_score - (candidates[1]["score"] if len(candidates) > 1 else 0.0)
            recognized = (
                bool(candidates)
                and best_score >= float(self.metadata["score_threshold"])
                and margin >= float(self.metadata["margin_threshold"])
            )
            attraction = self.catalog[candidates[0]["object_id"]] if recognized else None
            return {
                "recognized": recognized,
                "object": attraction,
                "score": best_score,
                "margin": margin,
                "candidates": candidates,
                "model_version": f"{self.metadata['model_name']}:{self.metadata['model_pretrained']}",
                "dataset_version": str(self.metadata["manifest_sha256"])[:12],
            }
