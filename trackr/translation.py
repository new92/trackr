"""Optional cached machine translation for free-form operator announcements.

Disabled by default: remote translation sends announcement text to a third party.
The dashboard works normally without the optional dependency/network service.
"""

from functools import lru_cache
import logging

LOGGER = logging.getLogger(__name__)


@lru_cache(maxsize=256)
def _translate_cached(text: str, target: str) -> str:
    from deep_translator import GoogleTranslator  # optional dependency

    return GoogleTranslator(source="el", target=target).translate(text)


def translate_dynamic(text: str, target: str, *, enabled: bool) -> str:
    if not enabled or target == "el" or not text:
        return text
    try:
        return _translate_cached(text[:1500], target) or text
    except Exception:
        LOGGER.warning("Dynamic translation failed; returning original Greek text")
        return text
