from fastapi.testclient import TestClient

import routing
from app import app

client = TestClient(app)
CENTER = {"latitude": 48.48, "longitude": 135.071}


def test_legacy_request_format_still_works():
    response = client.post("/api/plan-route", json={**CENTER, "limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert len(data["route"]) == 5
    assert data["start"] == CENTER
    first = data["route"][0]
    assert {"id", "name", "distance_from_previous_km", "coordinates"} <= first.keys()
    assert data["total_distance_km"] >= 0
    # Default walking route never pulls in remote expeditions.
    assert all(item["trip_profile"] == "urban" for item in data["route"])
    assert {item["municipality"] for item in data["route"]} == {"Хабаровск"}


def test_new_fields_and_totals_are_consistent():
    data = client.post("/api/plan-route", json={"object_ids": [1, 3, 4, 10, 17], "travel_mode": "walk"}).json()
    summary = data["summary"]
    assert summary["stops"] == 5
    legs = [item["leg"] for item in data["route"] if item["leg"]]
    assert data["route"][0]["leg"] is None
    assert summary["travel_minutes"] == sum(leg["travel_minutes"] for leg in legs)
    assert summary["visit_minutes"] == sum(item["visit_minutes"]["planned"] for item in data["route"])
    assert summary["total_minutes"] == summary["travel_minutes"] + summary["visit_minutes"]
    assert all(leg["mode"] == "walk" and leg["speed_kmh"] == 4.5 and leg["detour_factor"] == 1.25 for leg in legs)
    assert data["estimation"]["method"] == "offline_haversine_detour"
    assert data["warnings"] == []


def test_walk_speed_formula():
    leg = routing.estimate_leg(4.5, "walk", True, False)
    assert leg["estimated_road_km"] == 5.6
    assert leg["travel_minutes"] == 75  # 4.5 km * 1.25 / 4.5 km/h = 1.25 h


def test_car_city_and_intercity_speeds():
    city = routing.estimate_leg(10, "car", True, False)
    assert city["mode"] == "car_city" and city["travel_minutes"] == 30  # 12.5 km at 25 km/h
    region = routing.estimate_leg(100, "car", False, False)
    assert region["mode"] == "car_intercity" and region["travel_minutes"] == 150  # 150 km at 60 km/h
    remote = routing.estimate_leg(100, "car", False, True)
    assert remote["is_range"] and remote["travel_minutes_range"] == {"min": 150, "max": 300}


def test_remote_objects_get_ranges_and_warnings():
    data = client.post("/api/plan-route", json={"object_ids": [1, 29, 37], "travel_mode": "car"}).json()
    summary = data["summary"]
    assert summary["has_remote_objects"] is True
    assert summary["total_minutes_range"]["max"] > summary["total_minutes_range"]["min"]
    text = " ".join(data["warnings"])
    assert "не стоит объединять с городской прогулкой" in text
    assert "подготовительная оценка" in text


def test_walk_with_non_urban_objects_warns():
    data = client.post("/api/plan-route", json={"object_ids": [1, 29], "travel_mode": "walk"}).json()
    assert any("пешком" in warning for warning in data["warnings"])


def test_available_minutes_limits_stops():
    data = client.post(
        "/api/plan-route", json={**CENTER, "travel_mode": "car", "available_minutes": 120}
    ).json()
    assert data["summary"]["total_minutes"] <= 120
    assert data["summary"]["fits_available_time"] is True
    assert data["skipped_object_ids"]
    assert any("Не помещаются" in warning for warning in data["warnings"])


def test_municipality_filter_and_car_mode_excludes_remote():
    data = client.post(
        "/api/plan-route",
        json={**CENTER, "travel_mode": "car", "municipality": "Комсомольск-на-Амуре", "limit": 20},
    ).json()
    assert data["route"]
    assert {item["municipality"] for item in data["route"]} == {"Комсомольск-на-Амуре"}
    auto = client.post("/api/plan-route", json={**CENTER, "travel_mode": "car", "limit": 20}).json()
    assert all(item["trip_profile"] != "remote" for item in auto["route"])


def test_start_on_a_place_has_no_zero_leg():
    data = client.post("/api/plan-route", json={"latitude": 48.4725, "longitude": 135.049, "limit": 2}).json()
    assert data["route"][0]["id"] == 1
    assert data["route"][0]["leg"] is None
    assert data["route"][1]["leg"]["distance_km"] > 0


def test_invalid_route_requests():
    assert client.post("/api/plan-route", json={"limit": 3}).status_code == 422
    assert client.post("/api/plan-route", json={"latitude": 48.4}).status_code == 422
    assert client.post("/api/plan-route", json={**CENTER, "travel_mode": "boat"}).status_code == 422
    unknown = client.post("/api/plan-route", json={"object_ids": [1, 999]}).json()
    assert len(unknown["route"]) == 1
    assert any("999" in warning for warning in unknown["warnings"])


def test_object_detail_endpoint():
    data = client.get("/api/objects/37").json()["object"]
    assert data["content_available"] is True
    assert data["trip_profile"] == "remote"
    assert {"history", "packing", "sources", "verified_at", "best_months_label"} <= data.keys()
    assert client.get("/api/objects/999").status_code == 404
    listing = client.get("/api/objects").json()["objects"]
    assert {"short_description", "visit_label", "difficulty", "best_months"} <= listing[0].keys()
    assert "history" not in listing[0]
