"""FastAPI-level tests for /v1/predict."""

from __future__ import annotations

from datetime import date, timedelta


def _payload(**overrides):
    defaults = dict(
        train_number="12951",
        travel_date=(date.today() + timedelta(days=10)).isoformat(),
        source_station="BCT",
        dest_station="NDLS",
        ticket_class="3A",
        quota="GN",
        current_wl_position=12,
    )
    defaults.update(overrides)
    return defaults


def test_predict_happy_path(client):
    resp = client.post("/v1/predict", json=_payload())
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert 0.0 <= body["probability"] <= 1.0
    assert body["bucket"] in {"high", "medium", "low"}
    assert 0.0 <= body["confidence_lo"] <= body["confidence_hi"] <= 1.0
    assert body["model_version"]
    assert isinstance(body["warnings"], list)


def test_predict_validation_rejects_bad_class(client):
    resp = client.post("/v1/predict", json=_payload(ticket_class="XX"))
    assert resp.status_code == 422


def test_predict_validation_rejects_wl_out_of_range(client):
    resp = client.post("/v1/predict", json=_payload(current_wl_position=0))
    assert resp.status_code == 422


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_model_card_endpoint_returns_methodology(client):
    resp = client.get("/v1/model-card")
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_version"]
    assert "heuristic" in body["methodology"].lower()
    assert body["feature_list"]
    assert body["limitations"]
    assert body["disclaimer"]
