from catalog import load_catalog
from settings import get_settings


def test_catalog_has_44_unique_valid_objects():
    settings = get_settings()
    objects = load_catalog(settings.absolute(settings.catalog_path))
    assert len(objects) == 44
    assert len({item.id for item in objects}) == 44
    assert len({item.slug for item in objects}) == 44
    assert all(item.source_urls for item in objects)
    assert all(item.latitude is not None and item.longitude is not None for item in objects)
