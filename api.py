"""Backwards-compatible scraper entrypoint.

Use `trackr.scraper.MetroSource` and `trackr.service.MetroService` for new code.
"""

from trackr.scraper import MetroSource
from trackr.i18n import legacy_labels


def fetch() -> dict:
    return MetroSource().fetch()


def static() -> dict:
    return legacy_labels("el")
