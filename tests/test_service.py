from trackr.service import MetroService, unavailable_snapshot


def test_no_network_on_construction_and_refresh_after_ttl():
    clock = [0.0]
    calls = []

    def fetch():
        calls.append(True)
        return {"status": "ok", "fetched_at": str(len(calls)), "stations": []}

    service = MetroService(fetch, clock=lambda: clock[0], ttl=30, retry_seconds=10)
    assert calls == []
    assert service.get()["status"] == "ok"
    assert len(calls) == 1
    clock[0] = 29
    assert service.get()["fetched_at"] == "1"
    assert len(calls) == 1
    clock[0] = 31
    assert service.get()["fetched_at"] == "2"
    assert len(calls) == 2


def test_stale_cache_fallback_and_backoff():
    clock = [0.0]
    calls = []

    def fetch():
        calls.append(1)
        if len(calls) >= 2:
            raise RuntimeError("offline")
        return {"status": "ok", "fetched_at": "first", "stations": []}

    service = MetroService(fetch, clock=lambda: clock[0], ttl=30, retry_seconds=10)
    service.get()
    clock[0] = 31
    item = service.get()
    assert item["status"] == "stale"
    assert item["stale"] is True
    assert item["fetched_at"] == "first"
    clock[0] = 35
    assert service.get()["status"] == "stale"
    assert len(calls) == 2  # retry backoff


def test_initial_failure_unknown_status_and_retry():
    clock = [0.0]
    service = MetroService(lambda: (_ for _ in ()).throw(RuntimeError("offline")), clock=lambda: clock[0])
    snap = service.get()
    assert snap["status"] == "unavailable"
    assert snap["summary"]["stations_unknown"] == 18
    assert all(s["working"] is None for s in snap["stations"])
    assert service.health()["source_fresh"] is False


def test_return_value_cannot_mutate_internal_cache():
    service = MetroService(lambda: unavailable_snapshot() | {"status": "ok"})
    value = service.get()
    value["stations"].clear()
    assert len(service.get()["stations"]) == 18


def test_manual_force_refresh_has_minimum_spacing():
    clock = [0.0]
    calls = []

    def fetch():
        calls.append(1)
        return {"status": "ok", "fetched_at": str(len(calls)), "stations": []}

    service = MetroService(fetch, clock=lambda: clock[0], ttl=45)
    service.get()
    clock[0] = 5
    assert service.get(force=True)["fetched_at"] == "1"
    clock[0] = 11
    assert service.get(force=True)["fetched_at"] == "2"
