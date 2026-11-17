"""Flask application factory; safe to import without upstream network access."""

from __future__ import annotations

import copy
import math
import os

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from .i18n import LABELS, language_or_none, legacy_labels
from .scraper import MetroSource
from .service import MetroService
from .stations import nearest_station
from .translation import translate_dynamic


def _env_number(name: str, default: float, *, low: float, high: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) and low <= value <= high else default


def _get_language():
    language = request.args.get("lang", "el")
    if language_or_none(language) is None:
        raise BadRequest("Unsupported language. Supported: el, en, fr, de, es")
    return language


def _localized(payload: dict, language: str, *, machine_translation: bool) -> dict:
    result = copy.deepcopy(payload)
    for station in result["stations"]:
        station["name"] = station["name_el"] if language == "el" else station["name_en"]
    for elev in result["elevators"]:
        if language != "el":
            match = next((s for s in result["stations"] if s["name_el"] == elev["station"]), None)
            if match is not None:
                elev["station"] = match["name"]
    result["announcement"] = translate_dynamic(
        result["announcement"], language, enabled=machine_translation
    )
    state = result["service"]["state"]
    if state in LABELS[language]:
        result["service"]["display"] = LABELS[language][state]
    else:
        result["service"]["display"] = LABELS[language]["unknown"]
    result["language"] = language
    return result


def _valid_coord(value, low: float, high: float) -> bool:
    return (
        isinstance(value, (float, int))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and low <= value <= high
    )


def create_app(config: dict | None = None, *, fetcher=None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=2048,
        TRACKR_REFRESH_SECONDS=_env_number("TRACKR_REFRESH_SECONDS", 45, low=10, high=3600),
        TRACKR_RETRY_SECONDS=_env_number("TRACKR_RETRY_SECONDS", 15, low=1, high=300),
        TRACKR_HTTP_CONNECT_TIMEOUT=_env_number("TRACKR_HTTP_CONNECT_TIMEOUT", 3, low=0.5, high=30),
        TRACKR_HTTP_READ_TIMEOUT=_env_number("TRACKR_HTTP_READ_TIMEOUT", 8, low=1, high=120),
        TRACKR_MACHINE_TRANSLATION=os.getenv("TRACKR_MACHINE_TRANSLATION", "0") == "1",
        JSON_AS_ASCII=False,
    )
    if config:
        app.config.update(config)
    source = MetroSource(
        connect_timeout=app.config["TRACKR_HTTP_CONNECT_TIMEOUT"],
        read_timeout=app.config["TRACKR_HTTP_READ_TIMEOUT"],
    )
    service = MetroService(
        fetcher or source.fetch,
        ttl=app.config["TRACKR_REFRESH_SECONDS"],
        retry_seconds=app.config["TRACKR_RETRY_SECONDS"],
    )
    app.extensions["trackr_service"] = service

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "geolocation=(self), camera=(), microphone=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; base-uri 'self'; "
            "object-src 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        if request.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(BadRequest)
    def bad_request(exc):
        return jsonify(error="bad_request", message=exc.description), 400

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_exc):
        return jsonify(error="payload_too_large"), 413

    @app.get("/")
    def index():
        language = _get_language()
        return render_template("index.html", language=language, t=LABELS[language])

    @app.get("/api")
    def api():
        language = _get_language()
        result = _localized(
            service.get(force=request.args.get("refresh") == "1"), language,
            machine_translation=app.config["TRACKR_MACHINE_TRANSLATION"],
        )
        return jsonify(result), 503 if result["status"] == "unavailable" else 200

    @app.get("/api/static")
    def static_labels():
        return jsonify(legacy_labels(_get_language()))

    @app.post("/api/nearest")
    def nearest():
        # Supported for API consumers; the dashboard computes nearest locally.
        if not request.is_json:
            return jsonify(error="invalid_content_type", message="Expected application/json"), 415
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise BadRequest("Expected a JSON object")
        lat, lng = data.get("lat"), data.get("lng")
        language = data.get("lang", "el")
        if language_or_none(language) is None:
            raise BadRequest("Unsupported language")
        if not _valid_coord(lat, -90, 90) or not _valid_coord(lng, -180, 180):
            raise BadRequest("lat/lng must be finite numbers within valid coordinate ranges")
        station, distance = nearest_station(lat, lng)
        snapshot = service.get()
        observed = next((s for s in snapshot["stations"] if s["id"] == station.id), None)
        return jsonify({
            "id": station.id,
            "name": station.name_el if language == "el" else station.name_en,
            "lat": station.lat, "lng": station.lng,
            "distance_km": round(distance, 3),
            "status": observed["status"] if observed else "unknown",
            "working": observed["working"] if observed else None,
            "source_stale": snapshot["stale"],
        })

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    @app.get("/readyz")
    def readyz():
        health = service.health()
        return jsonify(health), 200 if health["source_fresh"] else 503

    return app
