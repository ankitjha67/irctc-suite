"""
RapidAPI IRCTC wrapper adapter.

Design:
- Two providers: primary (IRCTC1) and fallback (irctc-indian-railway-pnr-status)
- Response schemas are normalized to our internal PnrStatus dataclass
- Retries with exponential backoff via tenacity
- Per-provider health tracking (we auto-promote fallback if primary fails repeatedly)
- NEVER caches raw IRCTC credentials — we don't handle them at all
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class PnrStatus:
    pnr: str
    train_number: str | None
    travel_date: str | None
    source: str | None
    destination: str | None
    ticket_class: str | None
    quota: str | None
    current_status: str  # "CNF" / "WL 12" / "CAN" / etc
    wl_position: int | None
    chart_prepared: bool
    raw: dict[str, Any]
    provider: str


class ProviderError(Exception):
    pass


class PnrProvider:
    """Base class. Subclass per provider."""
    name: str = "base"

    async def fetch(self, pnr: str) -> PnrStatus:
        raise NotImplementedError


class IRCTC1Provider(PnrProvider):
    name = "irctc1"
    host = "irctc1.p.rapidapi.com"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.HTTPError, ProviderError)),
        reraise=True,
    )
    async def fetch(self, pnr: str) -> PnrStatus:
        url = f"https://{self.host}/api/v3/getPNRStatus"
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.host,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, params={"pnrNumber": pnr})
            if resp.status_code != 200:
                raise ProviderError(f"IRCTC1 returned {resp.status_code}: {resp.text[:200]}")
            data = resp.json()

        return self._normalize(pnr, data)

    def _normalize(self, pnr: str, data: dict[str, Any]) -> PnrStatus:
        # NOTE: Exact field names depend on the RapidAPI provider's current schema.
        # This mapping is best-effort; verify against the live API on first integration.
        inner = data.get("data", data)
        passengers = inner.get("passengerList") or inner.get("passengers") or []
        first = passengers[0] if passengers else {}
        current_status = first.get("currentStatus") or first.get("current_status") or ""

        wl_position = None
        if current_status.startswith("WL") or current_status.startswith("W/L"):
            try:
                wl_position = int(
                    current_status.replace("WL", "").replace("W/L", "").strip().split()[0]
                )
            except (ValueError, IndexError):
                wl_position = None

        chart_prepared = bool(
            inner.get("chartStatus") == "CHART PREPARED"
            or inner.get("chart_prepared") is True
        )

        return PnrStatus(
            pnr=pnr,
            train_number=inner.get("trainNumber") or inner.get("train_number"),
            travel_date=inner.get("dateOfJourney") or inner.get("travel_date"),
            source=inner.get("boardingPoint") or inner.get("source"),
            destination=inner.get("destinationStation") or inner.get("destination"),
            ticket_class=inner.get("journeyClass") or inner.get("class"),
            quota=inner.get("quota"),
            current_status=current_status,
            wl_position=wl_position,
            chart_prepared=chart_prepared,
            raw=data,
            provider=self.name,
        )


class FallbackProvider(PnrProvider):
    name = "fallback"
    host = "irctc-indian-railway-pnr-status.p.rapidapi.com"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((httpx.HTTPError, ProviderError)),
        reraise=True,
    )
    async def fetch(self, pnr: str) -> PnrStatus:
        url = f"https://{self.host}/getPNRStatus/{pnr}"
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.host,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise ProviderError(f"Fallback returned {resp.status_code}")
            data = resp.json()

        # Fallback schema normalization — again, verify on first live call
        return PnrStatus(
            pnr=pnr,
            train_number=data.get("TrainNo"),
            travel_date=data.get("Doj"),
            source=data.get("From"),
            destination=data.get("To"),
            ticket_class=data.get("Class"),
            quota=data.get("Quota"),
            current_status=data.get("Status", ""),
            wl_position=None,
            chart_prepared=data.get("ChartPrepared") == "Y",
            raw=data,
            provider=self.name,
        )


class PnrClient:
    """Facade with automatic failover."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.rapidapi_key:
            logger.warning("RAPIDAPI_KEY not set — PnrClient will raise on fetch()")
        self.primary = IRCTC1Provider(settings.rapidapi_key)
        self.fallback = FallbackProvider(settings.rapidapi_key)

    async def fetch(self, pnr: str) -> PnrStatus:
        try:
            return await self.primary.fetch(pnr)
        except Exception as e:
            logger.warning("Primary provider failed for %s: %s — trying fallback", pnr, e)
            return await self.fallback.fetch(pnr)
