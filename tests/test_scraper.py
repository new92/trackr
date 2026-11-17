from datetime import datetime, timezone
from pathlib import Path

import pytest

from trackr.scraper import (
    ScraperError,
    _elevator_status,
    _safely_resolve_url,
    parse_site,
)

FIXTURE = (Path(__file__).parent / "fixtures" / "metro_sample.html").read_text(encoding="utf-8")
NOW = datetime(2026, 11, 17, 13, 0, tzinfo=timezone.utc)


def station(data, name):
    return next(s for s in data["stations"] if s["id"] == name)


def test_parse_explicit_station_indicators_not_announcement_text():
    data = parse_site(FIXTURE, fetched_at=NOW)
    assert data["status"] == "ok"
    assert len(data["stations"]) == 18
    assert station(data, "new-railway-station")["status"] == "operational"
    assert station(data, "dimokratias")["status"] == "closed"
    assert station(data, "25is-martiou")["status"] == "operational"
    assert station(data, "mikra")["status"] == "operational"
    assert station(data, "nomarchia")["status"] == "unknown"
    assert data["service"]["state"] == "mixed"  # header contradicts explicit closure
    assert data["working"] is False  # a Boolean, never the old Greek string
    assert data["summary"]["stations_total"] == 18
    assert data["summary"]["stations_operational"] == 3
    assert data["summary"]["stations_closed"] == 1
    assert data["summary"]["stations_unknown"] == 14
    assert data["summary"]["elevators_operational"] == 2
    assert data["summary"]["elevators_out_of_service"] == 1
    assert data["summary"]["elevators_unknown"] == 15
    assert data["fetched_at"] == "2026-11-17T13:00:00Z"
    assert data["announcement_url"] == "https://www.thessmetro.gr/news/1"


def test_no_parsing_old_announcements_to_determine_status():
    # The date, future or past, cannot safely determine station operational status.
    html = FIXTURE.replace("Οι σταθμοί θα λειτουργούν με αλλαγές.", "Δημοκρατίας 2 Ιανουαρίου στις 16.00")
    data = parse_site(html)
    assert station(data, "dimokratias")["status"] == "closed"
    assert station(data, "new-railway-station")["status"] == "operational"


def test_missing_service_status_or_map_fails_cleanly():
    with pytest.raises(ScraperError):
        parse_site("<html><div class='interactive-map'></div></html>")
    with pytest.raises(ScraperError):
        parse_site("<div class='eventbox-header-operation-name'>Normal Operation</div>")


def test_bad_url_not_returned_from_source():
    data = parse_site(FIXTURE.replace("/news/1", "javascript:alert(1)"))
    assert data["announcement_url"] == ""
    assert _safely_resolve_url("https://evil.example/") == ""
    assert _safely_resolve_url("//www.thessmetro.gr/path") == "https://www.thessmetro.gr/path"


def test_unknown_elevator_status_does_not_claim_operational():
    assert _elevator_status("Αναμένεται έλεγχος") == "unknown"
    assert _elevator_status("Οι ανελκυστήρες λειτουργούν κανονικά") == "operational"
    assert _elevator_status("Προσωρινά εκτός λειτουργίας") == "out_of_service"


def test_incomplete_html_or_unknown_station_not_claimed_open():
    html = FIXTURE.replace("class=\"station-status kanoniki btn btn-primary\"", "class=\"station-status btn btn-primary\"", 1)
    data = parse_site(html)
    assert station(data, "new-railway-station")["status"] == "unknown"


def test_naive_time_rejected():
    with pytest.raises(ValueError):
        parse_site(FIXTURE, fetched_at=datetime(2026, 11, 17))
