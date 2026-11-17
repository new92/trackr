"""Trackr: Thessaloniki Metro service status dashboard."""


def create_app(*args, **kwargs):
    """Lazy import, so parser and cache code can be tested in isolation."""
    from .app import create_app as factory

    return factory(*args, **kwargs)


__all__ = ["create_app"]
