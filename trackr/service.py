"""On-demand TTL caching, serialized refresh, stale fallback and backoff."""

from __future__ import annotations

import copy
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Callable

from .stations import STATIONS

LOGGER = logging.getLogger(__name__)


def unavailable_snapshot() -> dict:
    stations = [
        {
            "id": s.id, "name": s.name_el, "name_el": s.name_el, "name_en": s.name_en,
            "lat": s.lat, "lng": s.lng, "section": s.section, "status": "unknown",
            "status_source": "unknown", "working": None,
            "elevator": {"status": "unknown", "message": "", "working": None},
        }
        for s in STATIONS
    ]
    return {
        "status": "unavailable", "source": "https://www.thessmetro.gr/", "fetched_at": None,
        "stale": True, "service": {"state": "unknown", "operator_state": "unknown", "message": ""},
        "operation": "", "working": None, "announcement": "", "announcement_url": "",
        "stations": stations,
        "elevators": [{"station": s["name_el"], "status": "", "working": None} for s in stations],
        "stationsWorking": 0, "elevatorsWorking": 0,
        "summary": {
            "stations_total": len(stations), "stations_operational": 0,
            "stations_closed": 0, "stations_unknown": len(stations),
            "elevators_total": len(stations), "elevators_operational": 0,
            "elevators_out_of_service": 0, "elevators_unknown": len(stations),
        },
    }


class MetroService:
    def __init__(self, fetcher: Callable[[], dict], *, ttl: float = 45.0,
                 retry_seconds: float = 15.0, clock: Callable[[], float] = time.monotonic):
        if ttl <= 0 or retry_seconds <= 0:
            raise ValueError("cache TTL and retry interval must be positive")
        self.fetcher = fetcher
        self.ttl = ttl
        self.retry_seconds = retry_seconds
        self.clock = clock
        self.lock = threading.Lock()
        self.snapshot: dict | None = None
        self.fetched_monotonic: float | None = None
        self.retry_after = 0.0
        self.last_failed = False

    def get(self, *, force: bool = False) -> dict:
        now = self.clock()
        if self._current(now, force=force):
            return self._view()
        with self.lock:
            now = self.clock()
            if self._current(now, force=force):
                return self._view()
            try:
                result = self.fetcher()
                if result.get("status") != "ok":
                    raise ValueError("Fetcher returned a non-success payload")
                self.snapshot = copy.deepcopy(result)
                self.fetched_monotonic = self.clock()
                self.retry_after = 0.0
                self.last_failed = False
            except Exception:
                LOGGER.exception("Metro status refresh failed")
                self.retry_after = self.clock() + self.retry_seconds
                self.last_failed = True
            return self._view()

    def _current(self, now: float, *, force: bool) -> bool:
        # Minimum 10 seconds between scrapes, even on a manual force-refresh.
        if (
            force and self.snapshot is not None and self.fetched_monotonic is not None
            and now - self.fetched_monotonic < 10
        ):
            return True
        if now < self.retry_after:
            return True
        return (
            self.snapshot is not None
            and self.fetched_monotonic is not None
            and not force
            and now - self.fetched_monotonic < self.ttl
        )

    def _view(self) -> dict:
        result = copy.deepcopy(self.snapshot) if self.snapshot is not None else unavailable_snapshot()
        now = self.clock()
        expired = self.fetched_monotonic is None or now - self.fetched_monotonic >= self.ttl
        stale = self.last_failed or expired
        result["stale"] = stale
        if self.snapshot is None:
            result["status"] = "unavailable"
        elif stale:
            result["status"] = "stale"
        if stale:
            result["notice"] = "Live updates unavailable. Status may be out of date."
        return result

    def health(self) -> dict:
        # Never performs an upstream request merely for health probing.
        result = self._view()
        return {
            "status": result["status"],
            "source_fresh": not result["stale"],
            "last_updated": result["fetched_at"],
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
