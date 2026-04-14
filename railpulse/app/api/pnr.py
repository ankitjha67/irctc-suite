"""
PNR tracking endpoints.

POST /v1/pnr/track   — fetch current status via RapidAPI, persist to the
                       railpulse.pnrs + railpulse.pnr_status_history tables.
GET  /v1/pnr/{pnr}   — return the latest known status for a tracked PNR,
                       reading from our local history table (no external
                       call — use track to refresh).
"""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.rate_limit import enforce_track_pnr_rate_limit
from app.api.schemas import TrackPnrRequest, TrackPnrResponse
from app.config import get_settings
from app.data.rapidapi_client import PnrClient
from app.db.connection import get_session
from app.db.repositories import pnrs as pnrs_repo
from app.db.repositories import trains as trains_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/pnr", tags=["pnr"])


# The PnrClient is a singleton so we don't build a new httpx client per request.
# Tests override this via FastAPI's dependency_overrides on ``get_pnr_client``.
_pnr_client_singleton: PnrClient | None = None


def get_pnr_client() -> PnrClient:
    global _pnr_client_singleton
    if _pnr_client_singleton is None:
        _pnr_client_singleton = PnrClient()
    return _pnr_client_singleton


@router.post("/track", response_model=TrackPnrResponse)
async def track_pnr(
    req: TrackPnrRequest,
    subject_key: str = Depends(enforce_track_pnr_rate_limit),
    session: AsyncSession = Depends(get_session),
    client: PnrClient = Depends(get_pnr_client),
) -> TrackPnrResponse:
    settings = get_settings()

    try:
        status_data = await client.fetch(req.pnr)
    except Exception as exc:
        logger.error("PNR fetch failed for %s: %s", req.pnr, exc)
        raise HTTPException(status_code=502, detail="Unable to fetch PNR status right now") from exc

    # Persist to DB (best-effort — fetching the PNR succeeded, we don't want
    # a transient DB failure to mask that). The session context still wraps
    # this, so on a real error the HTTP layer will see a 500.
    if not settings.disable_db:
        # 1. Lazy-seed the train row so future predictions get good priors.
        if status_data.train_number:
            await trains_repo.get_or_create(
                session,
                train_number=status_data.train_number,
                source_station=status_data.source,
                dest_station=status_data.destination,
            )

        # 2. Upsert the tracked PNR.
        await pnrs_repo.upsert_pnr(
            session,
            pnr=status_data.pnr,
            train_number=status_data.train_number,
            travel_date=_parse_travel_date(status_data.travel_date),
            source=status_data.source,
            destination=status_data.destination,
            ticket_class=status_data.ticket_class,
            quota=status_data.quota,
        )

        # 3. Append to the status history log.
        await pnrs_repo.record_status(
            session,
            pnr=status_data.pnr,
            wl_position=status_data.wl_position,
            status_code=_classify_status(status_data.current_status),
            status_text=status_data.current_status,
            raw_response=status_data.raw,
        )

        if status_data.chart_prepared:
            await pnrs_repo.mark_chart_prepared(
                session,
                pnr=status_data.pnr,
                final_status=_classify_status(status_data.current_status),
            )

    return TrackPnrResponse(
        pnr=status_data.pnr,
        train_number=status_data.train_number,
        travel_date=status_data.travel_date,
        current_status=status_data.current_status,
        wl_position=status_data.wl_position,
        chart_prepared=status_data.chart_prepared,
        source=status_data.source,
        destination=status_data.destination,
        provider=status_data.provider,
    )


@router.get("/{pnr}")
async def get_pnr(pnr: str, session: AsyncSession = Depends(get_session)) -> dict:
    settings = get_settings()
    if settings.disable_db:
        raise HTTPException(status_code=404, detail="Not found")

    result = await session.execute(
        text(
            """
            SELECT p.pnr, p.train_number, p.travel_date, p.source, p.destination,
                   p.class, p.quota, p.chart_prepared_at, p.final_status,
                   p.last_polled_at, p.poll_count
            FROM railpulse.pnrs p
            WHERE p.pnr = :pnr
            """
        ),
        {"pnr": pnr},
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail="PNR not tracked")

    history = await session.execute(
        text(
            """
            SELECT observed_at, wl_position, status_code, status_text
            FROM railpulse.pnr_status_history
            WHERE pnr = :pnr
            ORDER BY observed_at DESC
            LIMIT 50
            """
        ),
        {"pnr": pnr},
    )

    return {
        "pnr": row[0],
        "train_number": row[1],
        "travel_date": row[2].isoformat() if row[2] else None,
        "source": row[3],
        "destination": row[4],
        "class": row[5],
        "quota": row[6],
        "chart_prepared_at": row[7].isoformat() if row[7] else None,
        "final_status": row[8],
        "last_polled_at": row[9].isoformat() if row[9] else None,
        "poll_count": row[10],
        "history": [
            {
                "observed_at": h[0].isoformat() if h[0] else None,
                "wl_position": h[1],
                "status_code": h[2],
                "status_text": h[3],
            }
            for h in history
        ],
    }


def _parse_travel_date(value: str | None) -> date | None:
    if not value:
        return None
    # Best-effort parse — providers return either YYYY-MM-DD or DD-MM-YYYY.
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            from datetime import datetime

            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _classify_status(current_status: str) -> str:
    s = (current_status or "").upper().strip()
    if not s:
        return "UNK"
    if s.startswith(("WL", "W/L")):
        return "WL"
    if s.startswith(("CNF", "CONFIRM")):
        return "CNF"
    if s.startswith("RAC"):
        return "RAC"
    if s.startswith(("CAN", "CANC")):
        return "CAN"
    return s[:16]
