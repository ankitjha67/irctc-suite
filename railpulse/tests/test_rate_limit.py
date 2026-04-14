"""Rate-limit enforcement tests."""

from __future__ import annotations

from datetime import date, timedelta


def _predict_payload():
    return {
        "train_number": "12951",
        "travel_date": (date.today() + timedelta(days=10)).isoformat(),
        "source_station": "BCT",
        "dest_station": "NDLS",
        "ticket_class": "3A",
        "quota": "GN",
        "current_wl_position": 12,
    }


def test_sixth_prediction_same_ip_returns_429(client):
    payload = _predict_payload()

    # First 5 must succeed.
    for i in range(5):
        resp = client.post("/v1/predict", json=payload)
        assert resp.status_code == 200, f"request {i + 1} failed: {resp.text}"

    # 6th triggers the free-tier cap.
    sixth = client.post("/v1/predict", json=payload)
    assert sixth.status_code == 429
    assert "free tier" in sixth.text.lower() or "per day" in sixth.text.lower()


def test_tracked_pnr_cap_enforced(client, app_with_disabled_db):
    from app.api.pnr import get_pnr_client
    from app.data.rapidapi_client import PnrStatus

    class StubClient:
        async def fetch(self, pnr: str) -> PnrStatus:
            return PnrStatus(
                pnr=pnr,
                train_number="12951",
                travel_date="2026-05-01",
                source="BCT",
                destination="NDLS",
                ticket_class="3A",
                quota="GN",
                current_status="WL 5",
                wl_position=5,
                chart_prepared=False,
                raw={},
                provider="stub",
            )

    app_with_disabled_db.dependency_overrides[get_pnr_client] = lambda: StubClient()

    # Free tier: 2 tracked PNRs per day.
    assert client.post("/v1/pnr/track", json={"pnr": "1111111111"}).status_code == 200
    assert client.post("/v1/pnr/track", json={"pnr": "2222222222"}).status_code == 200
    # 3rd should trip the cap.
    third = client.post("/v1/pnr/track", json={"pnr": "3333333333"})
    assert third.status_code == 429
