"""Station manifest and browser/client-side location helpers.

Operator station names: https://www.thessmetro.gr/
Coordinates: original project + published OpenStreetMap-derived station positions
(https://thessalonikimetro.org/en/metro-map/ ; © OpenStreetMap contributors, ODbL).
Station names are canonical, independent of the order of upstream HTML elements.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Station:
    id: str
    name_el: str
    name_en: str
    lat: float
    lng: float
    section: str


# The first 11 stations are shared, then two terminate at Nea Elvetia,
# and five run on the Kalamaria branch. The latter opened on 27 August 2026.
STATIONS: tuple[Station, ...] = (
    Station("new-railway-station", "Νέος Σιδηροδρομικός Σταθμός", "New Railway Station", 40.6439516, 22.9287502, "shared"),
    Station("dimokratias", "Δημοκρατίας", "Dimokratias", 40.640951, 22.9344741, "shared"),
    Station("venizelou", "Βενιζέλου", "Venizelou", 40.637038, 22.9420217, "shared"),
    Station("agias-sofias", "Αγίας Σοφίας", "Agias Sofias", 40.6346834, 22.9464947, "shared"),
    Station("sintrivani", "Σιντριβάνι", "Sintrivani", 40.6308467, 22.9542157, "shared"),
    Station("panepistimio", "Πανεπιστήμιο", "Panepistimio", 40.6263423, 22.9605221, "shared"),
    Station("papafi", "Παπάφη", "Papafi", 40.6197492, 22.9630217, "shared"),
    Station("efkleidis", "Ευκλείδης", "Efkleidis", 40.6157951, 22.9605732, "shared"),
    Station("fleming", "Φλέμινγκ", "Fleming", 40.6119797, 22.9573395, "shared"),
    Station("analipsi", "Ανάληψη", "Analipsi", 40.6060329, 22.957921, "shared"),
    Station("25is-martiou", "25ης Μαρτίου", "25is Martiou", 40.601075, 22.9585311, "shared"),
    Station("voulgari", "Βούλγαρη", "Voulgari", 40.5952071, 22.9605947, "nea-elvetia"),
    Station("nea-elvetia", "Νέα Ελβετία", "Nea Elvetia", 40.5932339, 22.9685282, "nea-elvetia"),
    Station("nomarchia", "Νομαρχία", "Nomarchia", 40.59139, 22.95694, "kalamaria"),
    Station("kalamaria", "Καλαμαριά", "Kalamaria", 40.58472, 22.95309, "kalamaria"),
    Station("aretsou", "Αρετσού", "Aretsou", 40.57861, 22.95444, "kalamaria"),
    Station("nea-krini", "Νέα Κρήνη", "Nea Krini", 40.57250, 22.96111, "kalamaria"),
    Station("mikra", "Μίκρα", "Mikra", 40.56761, 22.96671, "kalamaria"),
)

BY_ID = {s.id: s for s in STATIONS}


def normalize_name(value: str) -> str:
    """Match Greek station labels ignoring accents, case and punctuation."""
    deaccented = "".join(
        c for c in unicodedata.normalize("NFD", value.casefold())
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^\w]+", "", deaccented, flags=re.UNICODE)


BY_NAME = {}
for _station in STATIONS:
    BY_NAME[normalize_name(_station.name_el)] = _station
    BY_NAME[normalize_name(_station.name_en)] = _station

# Alternative variants encountered in Greek operator material.
BY_NAME[normalize_name("25 Μαρτίου")] = BY_ID["25is-martiou"]
BY_NAME[normalize_name("25ης Μαρτιου")] = BY_ID["25is-martiou"]
BY_NAME[normalize_name("25th Martiou")] = BY_ID["25is-martiou"]
BY_NAME[normalize_name("Νέος Σιδηροδρομικός")] = BY_ID["new-railway-station"]
BY_NAME[normalize_name("Ευκλείδη")] = BY_ID["efkleidis"]


def match_station(value: str) -> Station | None:
    return BY_NAME.get(normalize_name(value))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def nearest_station(lat: float, lng: float) -> tuple[Station, float]:
    station = min(STATIONS, key=lambda s: haversine_km(lat, lng, s.lat, s.lng))
    return station, haversine_km(lat, lng, station.lat, station.lng)
