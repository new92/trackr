# Contributing to Trackr

Thanks for contributing. Please start with a focused issue explaining the
behavior and steps to reproduce. For code changes:

1. Create a branch from `main`, and use a Python 3.11+ virtual environment.
2. Run `python -m pip install -e '.[dev]'`.
3. Run `ruff check .` and `pytest -q` before submitting a pull request.
4. Include regression tests and sample HTML fixtures for scraper changes.
5. Update `README.md` when API fields, environment settings or user behavior change.

## Data integrity policy

- Never mark a station open unless a recognizable operator indicator supports it.
- Do not treat mentions in a free-form announcement as station status.
- Unknown, stale and source-unavailable statuses must remain clearly distinguished.
- Do not add third-party map tiles, analytics or geolocation requests without
  explaining the privacy implications and ensuring users explicitly opt in.
- Treat coordinates and station names as maintained, independently sourced data;
  never match station positions by the order of HTML elements.

Please be respectful of other contributors. Security reports belong in the
private channel documented in `SECURITY.md` rather than public issues.
