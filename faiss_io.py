from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from pathlib import Path

import faiss


def read_index(path: Path, temp_root: Path | None = None) -> faiss.Index:
    """Read FAISS through an ASCII path on Windows builds lacking Unicode I/O."""
    if os.name != "nt" or str(path).isascii():
        return faiss.read_index(str(path))
    root = temp_root if temp_root and str(temp_root).isascii() else Path(tempfile.gettempdir())
    temp_dir = root / "faiss-temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"read-{uuid.uuid4().hex}.faiss"
    shutil.copy2(path, temp_path)
    try:
        return faiss.read_index(str(temp_path))
    finally:
        temp_path.unlink(missing_ok=True)
