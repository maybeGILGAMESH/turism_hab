"""Check that recognition assets in this clone are byte-identical to the frozen stable version.

Expected values are pinned in reports/stable_assets.json (taken from the v2.0.0 backup manifest).
Exit code 0 means identical, 1 means a mismatch, 2 means an asset is missing.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINNED = ROOT / "reports" / "stable_assets.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def aggregate(folder: str) -> tuple[int, str]:
    base = ROOT / folder
    digest = hashlib.sha256()
    files = sorted(path for path in base.rglob("*") if path.is_file())
    for path in sorted(files, key=lambda item: item.relative_to(ROOT).as_posix()):
        relative = path.relative_to(ROOT).as_posix()
        digest.update(f"{relative},{path.stat().st_size},{sha256(path)}\n".encode())
    return len(files), digest.hexdigest()


def verify() -> int:
    pinned = json.loads(PINNED.read_text(encoding="utf-8"))
    status = 0
    for relative, expected in pinned["files"].items():
        path = ROOT / relative
        if not path.exists():
            print(f"MISSING  {relative}")
            status = max(status, 2)
            continue
        actual = sha256(path)
        ok = actual == expected
        print(f"{'OK      ' if ok else 'CHANGED '} {relative}  {actual}")
        status = status if ok else max(status, 1)
    for folder, expected in pinned["aggregates"].items():
        if not (ROOT / folder).exists():
            print(f"MISSING  {folder}/")
            status = max(status, 2)
            continue
        count, actual = aggregate(folder)
        ok = count == expected["files"] and actual == expected["aggregate_sha256"]
        print(f"{'OK      ' if ok else 'CHANGED '} {folder}/ ({count} files)  {actual}")
        status = status if ok else max(status, 1)
    print("RESULT:", {0: "assets identical to stable", 1: "assets differ", 2: "assets missing"}[status])
    return status


if __name__ == "__main__":
    sys.exit(verify())
