import requests
import pytest

from trackr.scraper import MAX_HTML_BYTES, MetroSource, ScraperError
from pathlib import Path

SAMPLE = (Path(__file__).parent / "fixtures" / "metro_sample.html").read_bytes()


class FakeResponse:
    def __init__(self, body=SAMPLE, code=200, encoding="utf-8"):
        self.body = body
        self.status_code = code
        self.encoding = encoding

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def iter_content(self, chunk_size):
        for start in range(0, len(self.body), chunk_size):
            yield self.body[start:start + chunk_size]


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_https_fixed_source_timeouts_and_no_redirects():
    session = FakeSession(FakeResponse(encoding="ISO-8859-1"))
    source = MetroSource(connect_timeout=2, read_timeout=4, session=session)
    result = source.fetch()
    assert result["summary"]["stations_total"] == 18
    url, opts = session.calls[0]
    assert url == "https://www.thessmetro.gr/"
    assert opts["allow_redirects"] is False
    assert opts["timeout"] == (2, 4)
    assert opts["stream"] is True


def test_source_http_non200():
    with pytest.raises(ScraperError):
        MetroSource(session=FakeSession(FakeResponse(code=502))).fetch()


def test_source_size_limit():
    with pytest.raises(ScraperError):
        MetroSource(session=FakeSession(FakeResponse(body=b"x" * (MAX_HTML_BYTES + 1)))).fetch()


def test_source_network_failure():
    with pytest.raises(ScraperError, match="request failed"):
        MetroSource(session=FakeSession(requests.exceptions.Timeout("offline"))).fetch()
