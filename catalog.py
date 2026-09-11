from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Attraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(ge=1)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=3)
    category: str
    municipality: str
    address: str = ""
    latitude: float | None = None
    longitude: float | None = None
    description: str = Field(min_length=20)
    access_notes: str = ""
    source_urls: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    enabled: bool = True
    index_status: str = "pending_index"

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float | None) -> float | None:
        if value is not None and not -90 <= value <= 90:
            raise ValueError("latitude must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float | None) -> float | None:
        if value is not None and not -180 <= value <= 180:
            raise ValueError("longitude must be between -180 and 180")
        return value


def load_catalog(path: str | Path) -> list[Attraction]:
    catalog_path = Path(path)
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    objects = [Attraction.model_validate(item) for item in raw]
    ids = [item.id for item in objects]
    slugs = [item.slug for item in objects]
    if len(ids) != len(set(ids)):
        raise ValueError("catalog contains duplicate ids")
    if len(slugs) != len(set(slugs)):
        raise ValueError("catalog contains duplicate slugs")
    return objects


def save_catalog(path: str | Path, objects: list[Attraction]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = [item.model_dump(mode="json") for item in sorted(objects, key=lambda item: item.id)]
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
