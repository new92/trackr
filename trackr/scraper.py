"""Isolated HTML parser for thessmetro.gr.

The site is not an official JSON API. Its DOM may change without notice.
Do not infer station closure from free-form announcement text.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .stations import STATIONS, match_station

LOGGER = logging.getLogger(__name__)
SOURCE_URL = "https://www.thessmetro.gr/"
USER_AGENT = "Trackr/3.0 (+https://github.com/new92/trackr; public status monitor)"
MAX_HTML_BYTES = 2_000_000


class ScraperError(RuntimeError):
    """Upstream data is unavailable or cannot be interpreted reliably."""


def _fold(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text.casefold())
        if unicodedata.category(c) != "Mn"
    )


def _safely_resolve_url(href: str) -> str:
    if not href:
        return ""
    absolute = urljoin(SOURCE_URL, href)
    parsed = urlparse(absolute)
    if parsed.scheme != "https" or parsed.hostname not in {"www.thessmetro.gr", "thessmetro.gr"}:
        return ""
    return absolute


def _state_from_classes(element) -> str:
    """Only classify explicitly marked station-status DOM nodes."""
    if element is None:
        return "unknown"
    classes = set(element.get("class", []))
    if "ektos" in classes:
        return "closed"
    if "kanoniki" in classes:
        return "operational"
    # These terms may be present as dedicated accessible labels in newer templates.
    explicit = _fold(str(element.get("data-bs-stationstatus", "")))
    if "εκτοσ λειτουργιασ" in explicit:
        return "closed"
    if "κανονικη λειτουργια" in explicit:
        return "operational"
    return "unknown"


def _elevator_status(text: str) -> str:
    folded = _fold(" ".join(text.split()))
    if any(phrase in folded for phrase in ("εκτοσ λειτουργιασ", "δεν λειτουργουν", "δεν λειτουργει")):
        return "out_of_service"
    if "λειτουργουν κανονικα" in folded or "λειτουργει κανονικα" in folded:
        return "operational"
    return "unknown"


def _service_state(text: str) -> str:
    normalized = _fold(" ".join(text.split()))
    if normalized == "κανονικη λειτουργια" or normalized == "normal operation":
        return "operational"
    if any(term in normalized for term in ("μερικη", "τροποποι", "partial", "limited")):
        return "limited"
    if any(term in normalized for term in ("αναστολη", "διακοπη", "εκτοσ λειτουργιασ", "suspend")):
        return "disrupted"
    return "unknown"


def parse_site(html: str, *, fetched_at: datetime | None = None) -> dict:
    """Parse an operator page into status, with unknown for missing station evidence."""
    soup = BeautifulSoup(html, "html.parser")
    header = soup.select_one(".eventbox-header-operation-name")
    if header is None or not header.get_text(strip=True):
        raise ScraperError("Operator service-status header missing")

    operation = header.get_text(" ", strip=True)
    service_state = _service_state(operation)
    ticker = soup.select_one(".ticker__item")
    announcement = ""
    announcement_url = ""
    if ticker:
        announcement = ticker.get_text(" ", strip=True).replace("\xa0", " ")
        announcement = re.sub(r"^\s*Ανακοίνωση\s*:\s*", "", announcement, flags=re.I)
        anchor = ticker.find("a", href=True)
        if anchor:
            announcement_url = _safely_resolve_url(anchor["href"])

    station_nodes = soup.select(".interactive-map li")
    if not station_nodes:
        raise ScraperError("Operator station map missing")

    observed: dict[str, dict] = {}
    for li in station_nodes:
        indicator = li.select_one(".station-status[data-bs-stationname]")
        if indicator is None:
            indicator = li.select_one("[data-bs-stationname]")
        if indicator is None:
            continue
        name = indicator.get("data-bs-stationname", "").strip()
        station = match_station(name)
        if station is None:
            LOGGER.warning("Unrecognized operator station: %s", name[:100])
            continue
        elevator_text = indicator.get("data-bs-elevator", "").strip()
        status = _state_from_classes(indicator)
        if status == "unknown":
            # On some versions, a dedicated child element carries the status.
            status = _state_from_classes(li.select_one(".station-status.kanoniki, .station-status.ektos"))
        observed[station.id] = {
            "status": status,
            "status_source": "operator_indicator" if status != "unknown" else "unknown",
            "elevator_status": _elevator_status(elevator_text),
            "elevator_message": elevator_text,
        }

    if not observed:
        raise ScraperError("No recognized stations found in operator map")

    stations = []
    for station in STATIONS:
        entry = observed.get(station.id, {})
        status = entry.get("status", "unknown")
        elevator_status = entry.get("elevator_status", "unknown")
        stations.append({
            "id": station.id,
            "name": station.name_el,
            "name_el": station.name_el,
            "name_en": station.name_en,
            "lat": station.lat,
            "lng": station.lng,
            "section": station.section,
            "status": status,
            "status_source": entry.get("status_source", "unknown"),
            "working": True if status == "operational" else False if status == "closed" else None,
            "elevator": {
                "status": elevator_status,
                "message": entry.get("elevator_message", ""),
                "working": True if elevator_status == "operational" else False if elevator_status == "out_of_service" else None,
            },
        })

    count = lambda key, value: sum(item[key] == value for item in stations)  # noqa: E731
    elev_count = lambda value: sum(item["elevator"]["status"] == value for item in stations)  # noqa: E731
    operational = count("status", "operational")
    closed = count("status", "closed")
    unknown = len(stations) - operational - closed
    elevators_operational = elev_count("operational")
    elevators_down = elev_count("out_of_service")
    elevators_unknown = len(stations) - elevators_operational - elevators_down
    conflicting = service_state == "operational" and closed > 0
    now = fetched_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("fetched_at must be timezone-aware")
    timestamp = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "status": "ok",
        "source": SOURCE_URL,
        "fetched_at": timestamp,
        "stale": False,
        "service": {
            "state": "mixed" if conflicting else service_state,
            "operator_state": service_state,
            "message": operation,
        },
        "operation": operation,
        "working": service_state == "operational" and not conflicting,
        "announcement": announcement,
        "announcement_url": announcement_url,
        "stations": stations,
        "elevators": [
            {"station": s["name_el"], "status": s["elevator"]["message"],
             "working": s["elevator"]["working"]} for s in stations
        ],
        "stationsWorking": operational,
        "elevatorsWorking": elevators_operational,
        "summary": {
            "stations_total": len(stations),
            "stations_operational": operational,
            "stations_closed": closed,
            "stations_unknown": unknown,
            "elevators_total": len(stations),
            "elevators_operational": elevators_operational,
            "elevators_out_of_service": elevators_down,
            "elevators_unknown": elevators_unknown,
        },
    }


class MetroSource:
    """Small, bounded, HTTPS-only operator-site client."""

    def __init__(self, *, connect_timeout: float = 3.0, read_timeout: float = 8.0,
                 session: requests.Session | None = None):
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.session = session or requests.Session()

    def fetch(self) -> dict:
        try:
            with self.session.get(
                SOURCE_URL,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
                timeout=(self.connect_timeout, self.read_timeout),
                stream=True,
                allow_redirects=False,
            ) as resp:
                if resp.status_code != 200:
                    raise ScraperError(f"Operator returned HTTP {resp.status_code}")
                content = bytearray()
                for chunk in resp.iter_content(chunk_size=65536):
                    content.extend(chunk)
                    if len(content) > MAX_HTML_BYTES:
                        raise ScraperError("Operator HTML size limit exceeded")
                encoding = resp.encoding or "utf-8"
                if encoding.lower() in {"latin-1", "iso-8859-1"}:
                    encoding = "utf-8"  # operator pages are encoded in UTF-8
                html = content.decode(encoding, errors="replace")
        except requests.RequestException as exc:
            raise ScraperError("Operator site request failed") from exc
        return parse_site(html)
