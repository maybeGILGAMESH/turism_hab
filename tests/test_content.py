import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from catalog import load_catalog
from place_content import PlaceContent, content_sha256, load_content, months_label
from settings import ROOT, get_settings

CONTENT = ROOT / "content"


def catalog_ids() -> set[int]:
    settings = get_settings()
    return {item.id for item in load_catalog(settings.absolute(settings.catalog_path))}


def test_all_44_objects_have_valid_cards():
    cards = load_content(CONTENT, catalog_ids())
    assert len(cards) == 44
    for object_id, card in cards.items():
        assert card["object_id"] == object_id
        assert card["visit_minutes"]["min"] <= card["visit_minutes"]["max"]
        assert all(1 <= month <= 12 for month in card["best_months"])
        assert card["seasons"], object_id
        assert card["sources"] and all(str(s["url"]).startswith("https://") for s in card["sources"])
        assert date.fromisoformat(card["verified_at"]) <= date.today()
        assert any(card["packing"][season] for season in ("summer", "winter", "offseason"))
        assert card["safety"] or card["etiquette"], object_id


def test_remote_objects_are_not_urban_and_have_long_visits():
    cards = load_content(CONTENT)
    remote = {object_id for object_id, card in cards.items() if card["trip_profile"] == "remote"}
    assert {35, 36, 37, 38, 41, 43} <= remote
    assert all(cards[object_id]["visit_minutes"]["min"] >= 180 for object_id in remote)


def test_content_is_separate_from_recognition_catalog():
    # Editorial text must never change the catalog hash that FAISS metadata pins.
    settings = get_settings()
    metadata_path = settings.absolute(settings.index_metadata_path)
    if not metadata_path.exists():
        pytest.skip("FAISS artifacts are not in Git (CI checkout)")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    import hashlib

    catalog_hash = hashlib.sha256(settings.absolute(settings.catalog_path).read_bytes()).hexdigest()
    assert metadata["catalog_sha256"] == catalog_hash
    assert "history" not in json.loads(settings.absolute(settings.catalog_path).read_text(encoding="utf-8"))[0]


def base_card(**overrides):
    card = json.loads((CONTENT / "places" / "01-khabarovsk.json").read_text(encoding="utf-8"))[0]
    card.update(overrides)
    return card


@pytest.mark.parametrize(
    "overrides",
    [
        {"visit_minutes": {"min": 90, "max": 30}},
        {"best_months": [0, 13]},
        {"sources": [{"title": "Plain HTTP", "url": "http://example.com", "kind": "official"}]},
        {"verified_at": "2999-01-01"},
        {"practical_tips": ["Билет стоит 500 руб."]},
        {"practical_tips": ["Открыто 10:00–18:00 ежедневно"]},
        {"difficulty": "extreme"},
    ],
)
def test_invalid_cards_are_rejected(overrides):
    with pytest.raises(ValidationError):
        PlaceContent.model_validate(base_card(**overrides))


def test_duplicate_or_orphan_content_is_rejected(tmp_path: Path):
    (tmp_path / "places").mkdir()
    (tmp_path / "profiles.json").write_text((CONTENT / "profiles.json").read_text(encoding="utf-8"), encoding="utf-8")
    card = base_card()
    (tmp_path / "places" / "a.json").write_text(json.dumps([card, card], ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_content(tmp_path)
    (tmp_path / "places" / "a.json").write_text(json.dumps([card], ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="mismatch"):
        load_content(tmp_path, {1, 2})


def test_content_version_ignores_line_endings(tmp_path: Path):
    for name in ("profiles.json",):
        (tmp_path / name).write_bytes((CONTENT / name).read_bytes().replace(b"\r\n", b"\n"))
    (tmp_path / "places").mkdir()
    for path in (CONTENT / "places").glob("*.json"):
        (tmp_path / "places" / path.name).write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    assert content_sha256(tmp_path) == content_sha256(CONTENT)


def test_months_label():
    assert months_label(list(range(1, 13))) == "круглый год"
    assert months_label([5, 6, 7, 8, 9]) == "май–сентябрь"
    assert months_label([1, 2, 12]) == "декабрь–февраль"
