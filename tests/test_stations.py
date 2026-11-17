from trackr.stations import STATIONS, haversine_km, match_station, nearest_station


def test_18_stations_and_unique_coordinates():
    assert len(STATIONS) == 18
    assert len({s.id for s in STATIONS}) == 18
    assert len({(s.lat, s.lng) for s in STATIONS}) == 18
    assert len([s for s in STATIONS if s.section == "kalamaria"]) == 5


def test_normalizes_greek_name_and_variations():
    assert match_station("ΔΗΜΟΚΡΑΤΙΑΣ").id == "dimokratias"
    assert match_station("25ης Μαρτίου").id == "25is-martiou"
    assert match_station("25 Μαρτίου").id == "25is-martiou"
    assert match_station("New Railway Station").id == "new-railway-station"
    assert match_station("Unknown station") is None


def test_nearest_for_new_branch_and_distance():
    mikra, d = nearest_station(40.56761, 22.96671)
    assert mikra.id == "mikra"
    assert d == 0.0
    assert 0.0 < haversine_km(40.56761, 22.96671, 40.57250, 22.96111) < 2
