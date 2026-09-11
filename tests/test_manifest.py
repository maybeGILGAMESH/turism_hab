from pathlib import Path

from data_pipeline import Manifest, assign_splits
from prepare_curated_dataset import choose_splits


def test_split_minimums(tmp_path: Path):
    manifest = Manifest(tmp_path / "manifest.csv")
    for index in range(20):
        manifest.add(
            {
                "object_id": 1,
                "object_name": "Test",
                "source_page_url": f"https://example/{index}",
                "sha256": f"{index:064x}",
                "status": "accepted",
            }
        )
    assign_splits(manifest)
    splits = [row["split"] for row in manifest.rows]
    assert splits.count("index") >= 10
    assert splits.count("validation") >= 3
    assert splits.count("test") >= 3


def test_curated_small_split_keeps_independent_test():
    rows = [
        {"object_id": "1", "sha256": f"{index:064x}"}
        for index in range(3)
    ]
    splits = choose_splits(rows)
    assert list(splits.values()).count("test") == 1
    assert list(splits.values()).count("index") == 2
    assert list(splits.values()).count("validation") == 0
