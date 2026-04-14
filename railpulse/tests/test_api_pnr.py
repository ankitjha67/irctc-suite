"""Tests for /v1/pnr/track with a stub RapidAPI provider."""

from __future__ import annotations

from app.api.pnr import get_pnr_client
from app.data.rapidapi_client import PnrStatus


class StubClient:
    def __init__(self, status: PnrStatus):
        self._status = status

    async def fetch(self, pnr: str) -> PnrStatus:
        return self._status


def _stub_status(pnr: str = "1234567890") -> PnrStatus:
    return PnrStatus(
        pnr=pnr,
        train_number="12951",
        travel_date="2026-05-01",
        source="BCT",
        destination="NDLS",
        ticket_class="3A",
        quota="GN",
        current_status="WL 12",
        wl_position=12,
        chart_prepared=False,
        raw={"mock": True},
        provider="stub",
    )


def test_track_pnr_happy_path(client, app_with_disabled_db):
    app_with_disabled_db.dependency_overrides[get_pnr_client] = lambda: StubClient(_stub_status())

    resp = client.post("/v1/pnr/track", json={"pnr": "1234567890"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["pnr"] == "1234567890"
    assert body["train_number"] == "12951"
    assert body["current_status"] == "WL 12"
    assert body["wl_position"] == 12
    assert body["chart_prepared"] is False
    assert body["provider"] == "stub"


def test_track_pnr_validation_rejects_short_pnr(client):
    resp = client.post("/v1/pnr/track", json={"pnr": "123"})
    assert resp.status_code == 422


def test_track_pnr_validation_rejects_non_numeric_pnr(client):
    resp = client.post("/v1/pnr/track", json={"pnr": "abcdefghij"})
    assert resp.status_code == 422


def test_track_pnr_upstream_error_returns_502(client, app_with_disabled_db):
    class FailingClient:
        async def fetch(self, pnr: str) -> PnrStatus:
            raise RuntimeError("upstream unavailable")

    app_with_disabled_db.dependency_overrides[get_pnr_client] = lambda: FailingClient()

    resp = client.post("/v1/pnr/track", json={"pnr": "1234567890"})
    assert resp.status_code == 502
