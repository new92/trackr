# Changelog

## 3.0.0 — 2026-11-17 (upgraded ZIP build)

- Rebuilt the Flask backend with an application factory and lazy status fetching.
- Fixed the original `"ΟΧΙ"` truthiness bug and replaced hardcoded totals.
- Added an 18-station manifest including the Kalamaria extension.
- Separated operator station indicators from elevator indicators.
- Removed guesswork based on free-form announcements and dates.
- Added cache TTL, upstream timeout/size limits, stale fallback and retry backoff.
- Added server-side validation, language isolation, response security headers,
  compatibility endpoints and explicit API freshness states.
- Added pretranslated labels in five languages and optional cached announcement
  translation, disabled by default.
- Redesigned the UI with a self-hosted schematic map, search, favorites, local
  nearest-station geolocation, optional in-tab notifications and light/dark modes.
- Added parser, cache and Flask integration tests; GitHub Actions, Ruff,
  Dependabot and dependency auditing; secure Docker/Gunicorn deployment.
- Corrected README installation and repository links; added security,
  contributing and code-of-conduct documentation.

### Known limitations

- The upstream operator site is HTML, not a stable JSON service. Trackr can
  become temporarily unable to parse it after layout changes.
- Station lift indicators reflect the operator's per-station status, not the
  count of individual lift shafts.
- Alerts are only delivered while the dashboard tab is open; push delivery to
  closed browsers is intentionally not implemented.
- All nearest-station distances are straight-line approximations.
