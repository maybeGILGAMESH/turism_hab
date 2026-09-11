from __future__ import annotations

import hashlib
from pathlib import Path

import open_clip

OPENAI_VIT_B_16_SHA256 = "5806e77cd80f8b59890b7e101eabd078d9fb84e6937f9e85e4ecb61988df416f"


def _valid_checkpoint(path: Path) -> bool:
    if not path.exists() or path.stat().st_size != 350_837_078:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == OPENAI_VIT_B_16_SHA256


def create_clip_model(model_name: str, pretrained: str, cache_dir: Path):
    """Prefer the verified local OpenAI checkpoint, with online lookup as installer fallback."""
    checkpoint = cache_dir / f"{model_name}.pt"
    weights = str(checkpoint) if _valid_checkpoint(checkpoint) else pretrained
    return open_clip.create_model_and_transforms(
        model_name,
        pretrained=weights,
        cache_dir=str(cache_dir),
        # The official OpenAI checkpoint is a TorchScript archive. Its SHA-256 is
        # verified above before allowing the legacy loader required by PyTorch 2.6+.
        weights_only=weights != str(checkpoint),
    )
