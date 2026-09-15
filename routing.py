"""Offline route time estimation (no road graph, no network)."""

from __future__ import annotations

import math
from dataclasses import dataclass

WALK_KMH = 4.5
CAR_CITY_KMH = 25.0
CAR_INTERCITY_KMH = 60.0
CITY_DETOUR = 1.25
REGION_DETOUR = 1.5
REMOTE_RANGE_FACTOR = 2.0
SAME_AREA_KM = 20.0
WALK_WARNING_KM = 6.0
LONG_DRIVE_KM = 300.0

ESTIMATION = {
    "method": "offline_haversine_detour",
    "description": (
        "Расстояние по прямой между координатами умножается на коэффициент непрямого маршрута "
        "и делится на среднюю скорость. Пробки, паромы, расписания, погода и состояние дорог "
        "не учитываются — это подготовительная оценка, а не навигация."
    ),
    "speeds_kmh": {"walk": WALK_KMH, "car_city": CAR_CITY_KMH, "car_intercity": CAR_INTERCITY_KMH},
    "detour_factors": {"city": CITY_DETOUR, "regional": REGION_DETOUR},
    "remote_range_factor": REMOTE_RANGE_FACTOR,
}


@dataclass(frozen=True)
class Place:
    id: int
    name: str
    latitude: float
    longitude: float
    municipality: str
    trip_profile: str = "urban"
    visit_min: int = 30
    visit_max: int = 60

    @property
    def remote(self) -> bool:
        return self.trip_profile == "remote"

    @property
    def planned_visit(self) -> int:
        if self.remote:
            return self.visit_min
        return max(self.visit_min, int(round((self.visit_min + self.visit_max) / 2 / 5) * 5))


def haversine_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    radius = 6371.0
    dlat, dlon = math.radians(b_lat - a_lat), math.radians(b_lon - a_lon)
    value = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(a_lat)) * math.cos(math.radians(b_lat)) * math.sin(dlon / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def estimate_leg(distance_km: float, travel_mode: str, same_settlement: bool, remote: bool) -> dict[str, object]:
    if travel_mode == "walk":
        kind, speed, detour = "walk", WALK_KMH, CITY_DETOUR
    elif same_settlement:
        kind, speed, detour = "car_city", CAR_CITY_KMH, CITY_DETOUR
    else:
        kind, speed, detour = "car_intercity", CAR_INTERCITY_KMH, REGION_DETOUR
    road_km = distance_km * detour
    minutes = road_km / speed * 60
    high = minutes * REMOTE_RANGE_FACTOR if remote else minutes
    return {
        "distance_km": round(distance_km, 2),
        "estimated_road_km": round(road_km, 1),
        "travel_minutes": round(minutes),
        "travel_minutes_range": {"min": round(minutes), "max": round(high)},
        "mode": kind,
        "speed_kmh": speed,
        "detour_factor": detour,
        "is_range": remote,
    }


def _names(places: list[Place]) -> str:
    return ", ".join(place.name for place in places)


def plan_route(
    places: list[Place],
    *,
    start: tuple[float, float] | None,
    travel_mode: str = "walk",
    limit: int = 10,
    object_ids: list[int] | None = None,
    municipality: str | None = None,
    available_minutes: int | None = None,
) -> dict[str, object]:
    by_id = {place.id: place for place in places}
    warnings: list[str] = []
    explicit = bool(object_ids)

    if explicit:
        unknown = [value for value in object_ids if value not in by_id]
        if unknown:
            warnings.append(f"Объекты не найдены и пропущены: {', '.join(map(str, unknown))}.")
        pool = [by_id[value] for value in dict.fromkeys(object_ids) if value in by_id]
        remote = [place for place in pool if place.remote]
        if remote and len(remote) < len(pool):
            warnings.append(
                "Удалённые природные объекты не стоит объединять с городской прогулкой: "
                f"{_names(remote)}. Планируйте их отдельной поездкой."
            )
        if travel_mode == "walk" and any(place.trip_profile != "urban" for place in pool):
            warnings.append("Часть мест недоступна пешком из города — для них выберите режим «автомобиль».")
        if travel_mode == "walk" and len({place.municipality for place in pool}) > 1:
            warnings.append("Места находятся в разных населённых пунктах: пешая прогулка между ними невозможна.")
    else:
        pool = list(places)
        if municipality:
            wanted = municipality.strip().lower()
            pool = [place for place in pool if place.municipality.lower() == wanted]
            if not pool:
                warnings.append(f"В каталоге нет мест с муниципалитетом «{municipality}».")
        pool = [place for place in pool if not place.remote]
        if travel_mode == "walk":
            pool = [place for place in pool if place.trip_profile == "urban"]
        if start and pool and not municipality:
            nearest = min(pool, key=lambda place: haversine_km(*start, place.latitude, place.longitude))
            if travel_mode == "walk" or haversine_km(*start, nearest.latitude, nearest.longitude) <= SAME_AREA_KM:
                pool = [place for place in pool if place.municipality == nearest.municipality]

    stops: list[dict[str, object]] = []
    skipped: list[Place] = []
    remaining = list(pool)
    elapsed = 0
    current: tuple[float, float] | None = start
    previous: Place | None = None

    # Without a start point the route begins at the first requested object.
    while current is None and remaining:
        first = remaining.pop(0)
        visit = first.planned_visit
        if available_minutes is not None and visit > available_minutes:
            skipped.append(first)
            continue
        stops.append(_stop(first, None, 0, visit))
        elapsed = visit
        current, previous = (first.latitude, first.longitude), first

    while remaining and current is not None and (explicit or len(stops) < limit):
        nxt = min(remaining, key=lambda place: haversine_km(*current, place.latitude, place.longitude))
        remaining.remove(nxt)
        distance = haversine_km(*current, nxt.latitude, nxt.longitude)
        same = previous.municipality == nxt.municipality if previous else distance <= SAME_AREA_KM
        # A start point that coincides with the first place is not a real transfer.
        leg = (
            None
            if not stops and distance < 0.05
            else estimate_leg(distance, travel_mode, same, nxt.remote or bool(previous and previous.remote))
        )
        travel = int(leg["travel_minutes"]) if leg else 0
        visit = nxt.planned_visit
        if available_minutes is not None and elapsed + travel + visit > available_minutes:
            skipped.append(nxt)
            continue
        stops.append(_stop(nxt, leg, elapsed + travel, visit))
        elapsed += travel + visit
        current, previous = (nxt.latitude, nxt.longitude), nxt

    legs = [stop["leg"] for stop in stops if stop["leg"]]
    if travel_mode == "walk" and any(float(leg["estimated_road_km"]) > WALK_WARNING_KM for leg in legs):
        warnings.append(f"Есть пешие переходы длиннее {WALK_WARNING_KM:g} км — подумайте о транспорте.")
    if any(float(leg["estimated_road_km"]) > LONG_DRIVE_KM for leg in legs):
        warnings.append(
            "В маршруте есть переезд длиннее 300 км: сравните автомобиль с поездом или самолётом "
            "и проверьте расписания у перевозчиков."
        )
    if any(by_id[int(stop["object_id"])].remote for stop in stops):
        warnings.append(
            "Для удалённых объектов показан диапазон времени. Это подготовительная оценка, а не дорожная "
            "навигация: заброска зависит от погоды, сезона, транспорта и разрешений."
        )
    if skipped:
        shown = _names(skipped[:3]) + (f" и ещё {len(skipped) - 3}" if len(skipped) > 3 else "")
        warnings.append(f"Не помещаются в {available_minutes} мин: {shown}.")
    if not stops and not warnings:
        warnings.append("Не удалось подобрать места для маршрута с заданными условиями.")

    travel = sum(int(leg["travel_minutes"]) for leg in legs)
    travel_low = sum(int(leg["travel_minutes_range"]["min"]) for leg in legs)
    travel_high = sum(int(leg["travel_minutes_range"]["max"]) for leg in legs)
    visit_planned = sum(int(stop["visit_minutes"]["planned"]) for stop in stops)
    visit_low = sum(int(stop["visit_minutes"]["min"]) for stop in stops)
    visit_high = sum(int(stop["visit_minutes"]["max"]) for stop in stops)
    total = travel + visit_planned
    return {
        "stops": stops,
        "summary": {
            "stops": len(stops),
            "distance_km": round(sum(float(leg["distance_km"]) for leg in legs), 2),
            "estimated_road_km": round(sum(float(leg["estimated_road_km"]) for leg in legs), 1),
            "travel_minutes": travel,
            "travel_minutes_range": {"min": travel_low, "max": travel_high},
            "visit_minutes": visit_planned,
            "visit_minutes_range": {"min": visit_low, "max": visit_high},
            "total_minutes": total,
            "total_minutes_range": {"min": travel_low + visit_low, "max": travel_high + visit_high},
            "available_minutes": available_minutes,
            "fits_available_time": None if available_minutes is None else total <= available_minutes,
            "has_remote_objects": any(by_id[int(stop["object_id"])].remote for stop in stops),
        },
        "warnings": warnings,
        "skipped_object_ids": [place.id for place in skipped],
        "estimation": ESTIMATION,
    }


def _stop(place: Place, leg: dict[str, object] | None, arrival: int, visit: int) -> dict[str, object]:
    return {
        "object_id": place.id,
        "name": place.name,
        "leg": leg,
        "arrival_after_minutes": arrival,
        "visit_minutes": {"min": place.visit_min, "max": place.visit_max, "planned": visit},
    }


def format_minutes(value: int) -> str:
    if value < 60:
        return f"{value} мин"
    hours, minutes = divmod(value, 60)
    if hours >= 48:
        days, hours = divmod(hours, 24)
        return f"{days} дн {hours} ч" if hours else f"{days} дн"
    return f"{hours} ч {minutes} мин" if minutes else f"{hours} ч"
