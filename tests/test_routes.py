"""Flask integration tests (require `pip install -e '.[dev]'`)."""
import pytest

pytest.importorskip("flask")

from trackr.app import create_app  # noqa: E402
from trackr.scraper import parse_site  # noqa: E402
from pathlib import Path  # noqa: E402

HTML = (Path(__file__).parent / "fixtures" / "metro_sample.html").read_text(encoding="utf-8")


@pytest.fixture
def client():
    calls = []

    def fetcher():
        calls.append(1)
        return parse_site(HTML)

    app = create_app({"TESTING": True, "TRACKR_MACHINE_TRANSLATION": False}, fetcher=fetcher)
    app.test_fetch_calls = calls
    return app.test_client()


def test_index_is_lazy_and_localized(client):
    response = client.get("/?lang=en")
    assert response.status_code == 200
    assert b"Know your route" in response.data
    assert b"lang=\"en\"" in response.data
    assert client.application.test_fetch_calls == []


def test_api_data_and_headers(client):
    response = client.get("/api?lang=en")
    assert response.status_code == 200
    result = response.get_json()
    assert result["stations"][0]["name"] == "New Railway Station"
    assert result["stations"][0]["working"] is True
    assert result["stations"][1]["working"] is False
    assert response.headers["Cache-Control"] == "no-store"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_invalid_language_and_input_rejected(client):
    assert client.get("/api?lang=xyz").status_code == 400
    assert client.get("/?lang=script").status_code == 400
    assert client.post("/api/nearest", json={"lat": "no", "lng": 23}).status_code == 400
    assert client.post("/api/nearest", json={"lat": 91, "lng": 23}).status_code == 400
    assert client.post("/api/nearest", json={"lat": True, "lng": 23}).status_code == 400
    assert client.post("/api/nearest", data="hello").status_code == 415


def test_nearest_api_and_localized_static_text(client):
    result = client.post("/api/nearest", json={"lat": 40.56761, "lng": 22.96671, "lang": "en"})
    assert result.status_code == 200
    assert result.get_json()["id"] == "mikra"
    assert result.get_json()["distance_km"] == 0.0
    labels = client.get("/api/static?lang=fr").get_json()
    assert labels["all"] == "Toutes"
    assert labels["station"] == "Station"


def test_failure_still_renders_dashboard_and_reports_503():
    app = create_app({"TESTING": True}, fetcher=lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    client = app.test_client()
    assert client.get("/").status_code == 200
    response = client.get("/api")
    assert response.status_code == 503
    assert response.get_json()["status"] == "unavailable"
    assert client.get("/readyz").status_code == 503
    assert client.get("/healthz").status_code == 200
