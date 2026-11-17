# trackr 🚇

**An independent Thessaloniki Metro status dashboard.** Station availability,
elevator information, announcements, and a clickable schematic of all **18**
current stations (including the five-station Kalamaria branch opened in 2026).

Trackr reads public information from [the metro operator](https://www.thessmetro.gr/).
It is **not affiliated with or endorsed by THEMA** and is **not a safety-critical
or guaranteed real-time service**. Always verify important travel decisions with
the operator, especially when data is marked *unknown* or *stale*.

## What changed in v3

- Correct Boolean status reporting; station statuses and lift statuses are distinct.
- All 18 stations are identified **by name**, not HTML list position or hardcoded totals.
- No more guessing station closures from the text or date of an announcement.
- Automatic, TTL-cached refresh with safe backoff and stale snapshot fallback.
- External requests have connection/read timeouts and a 2 MB response-size cap.
- Failed page parsing surfaces **unknown**, never an invented “all clear”.
- Five user-interface languages (Greek, English, French, German, Spanish).
- Responsive dashboard, searchable stations, accessible status indicators and
  an interactive **schematic** network diagram without external map tiles.
- Optional favorite stations (saved only in the browser), light/dark themes,
  and opt-in alerts when **this tab is open**.
- Nearest station calculated **locally in the browser** after a user action.
- Input validation, security headers, configurable settings, tests and CI.
- Optional machine translation of live Greek announcements with cached results.

## Install

Requires **Python 3.11+**. Linux, macOS, and Windows:

```bash
# Extract the supplied upgraded ZIP and open its project folder first:
cd trackr-upgraded
python -m venv .venv
```

Activate the environment:

```bash
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install and run (no `sudo` required):

```bash
python -m pip install -r requirements.txt
python interface.py
```

Open **http://127.0.0.1:5000/?lang=en** (Greek is the default).

The first status request contacts the public operator site. The application
starts even if the operator is offline; in that case all statuses will be
marked unknown until a refresh succeeds.

### Optional machine translation

Interface labels and common state names are translated **offline**. Live,
free-form announcements are originally in Greek. To enable third-party machine
translation of these announcements:

```bash
python -m pip install -e '.[translation]'
# set the environment variable before starting
export TRACKR_MACHINE_TRANSLATION=1     # macOS / Linux
# $env:TRACKR_MACHINE_TRANSLATION='1'   # Windows PowerShell
python interface.py
```

With this enabled, a third-party translator receives Greek announcement text;
results are cached and failures fall back to Greek. The feature is disabled by
default to avoid unexpected network calls and privacy disclosures. It is not
needed for station names or application labels.

### Docker

```bash
docker build -t trackr .
docker run --rm -p 8000:8000 trackr
```

Open **http://127.0.0.1:8000/**. The image uses Gunicorn as a non-root user.
`/healthz` checks application liveness; `/readyz` reports availability of a
fresh operator snapshot and initially responds 503 until data has been fetched.
For production, deploy behind an HTTPS reverse proxy and configure TLS and
request logging according to your environment.

### Production (without Docker)

```bash
python -m pip install -e '.[server]'
gunicorn --bind 127.0.0.1:8000 --workers 1 --threads 4 'trackr.app:create_app()'
```

Each Gunicorn **process** has its own in-memory cache. Using one worker reduces
scrape traffic; a shared Redis cache or background refresh worker is an option
if deploying at larger scale. The TTL refresh is *on demand*, not an always-on
background job.

## API

| Endpoint | Method | Behavior |
| --- | --- | --- |
| `/` | GET | Dashboard; optional `?lang=el|en|fr|de|es` |
| `/api` | GET | Latest cached source snapshot; `?lang=` selects display names |
| `/api/static` | GET | Translated UI strings and legacy aliases; `?lang=` supported |
| `/api/nearest` | POST | Backwards-compatible nearest-station calculation |
| `/healthz` | GET | HTTP 200 if the app is running |
| `/readyz` | GET | HTTP 200 when a fresh source snapshot exists; 503 otherwise |

Example:

```bash
curl 'http://127.0.0.1:5000/api?lang=en'
curl -X POST 'http://127.0.0.1:5000/api/nearest' \
  -H 'Content-Type: application/json' \
  -d '{"lat":40.61,"lng":22.96,"lang":"en"}'
```

A successful `/api` result includes `status`, `source`, `fetched_at` (UTC ISO
8601), `stale`, `service`, `announcement`, `announcement_url`, `stations`, and
`summary`. A station contains `id`, `name`, `name_el`, `name_en`, `lat`, `lng`,
`section`, `status`, `status_source`, `working`, and an `elevator` object.

Station `status` can be `operational`, `closed`, or `unknown`. Elevator `status`
can be `operational`, `out_of_service`, or `unknown`. `working` is a Boolean or
`null` if unverified — **not** the strings `"ΝΑΙ"` / `"ΟΧΙ"`.

Service `state` can be `operational`, `limited`, `disrupted`, `mixed`, or
`unknown`; `mixed` means the operator's general status says normal while one
or more explicit station indicators say closed.

`summary` counts only **verified** operational/closed/out-of-service states and
includes unknowns separately. The operator's elevator indicator is per
**station**, not a count of all individual lift shafts. Legacy fields
`stationsWorking`, `elevatorsWorking`, and `elevators` are maintained for
compatibility, but clients should migrate to `summary` and `stations`.

When no operator snapshot can be obtained, `/api` returns HTTP **503** with an
`unavailable` payload and 18 unknown stations. When using a cached snapshot
after an unsuccessful refresh, it returns HTTP **200** with `status: "stale"`
and `stale: true`. Clients must not silently treat stale data as current.

`/api/nearest` requires a valid JSON object containing numeric latitude and
longitude; values outside latitude ±90 / longitude ±180 are rejected with 400.
**The dashboard itself does not use this endpoint to locate the user.**

## Configuration

All settings are optional environment variables; see [`.env.example`](.env.example).

| Name | Default | Description |
| --- | --- | --- |
| `TRACKR_REFRESH_SECONDS` | `45` | Server cache TTL (10–3600 seconds) |
| `TRACKR_RETRY_SECONDS` | `15` | Minimum delay after an unsuccessful scrape (1–300 seconds) |
| `TRACKR_HTTP_CONNECT_TIMEOUT` | `3` | Upstream connect timeout, seconds |
| `TRACKR_HTTP_READ_TIMEOUT` | `8` | Upstream read timeout, seconds |
| `TRACKR_MACHINE_TRANSLATION` | `0` | Set to `1` to enable optional announcement translation |
| `TRACKR_HOST` | `127.0.0.1` | Development server bind address |
| `TRACKR_PORT` | `5000` | Development server port |

The frontend polls while visible at the configured refresh interval. Manual
refresh can request a new scrape after a minimum server-side cooling period,
so repeated clicking cannot overwhelm the operator's website. A hard reload
is not required to see service changes.

## Security and privacy

- Browser geolocation is requested **only** when you press “Find nearest
  station”. It is used locally and not stored or sent to Trackr by the UI.
- Favorite IDs, alert preferences and theme are stored in **browser
  `localStorage`**. No accounts, cookies, tracking scripts, or analytics.
- Browser notifications require explicit permission. They can report service
  transitions and disruptions at favorite stations while the page is open.
  This is **not** background push notification delivery.
- The schematic network map is self-hosted SVG; no third-party tiles or map
  requests. Coordinates are geographic points, and “nearest” means straight-line
  distance, not walking time or an accessible route.
- Only fixed upstream URL `https://www.thessmetro.gr/` is scraped. Remote
  announcement links are restricted to the official HTTPS host.
- The operator may modify its HTML without advance notice. Trackr detects
  missing required fields and shows stale or unknown status rather than
  inferring from announcements.

See [`SECURITY.md`](SECURITY.md) for private vulnerability reporting.

## Development and tests

```bash
python -m pip install -e '.[dev]'
ruff check .
python -m pytest -q
node --check trackr/static/app.js   # optional JS syntax check (Node installed)
```

CI runs tests on Python 3.11, 3.12 and 3.13, checks Ruff and runs a dependency
audit. Scraper tests use stored fixture HTML and do not contact the operator.
If the upstream page changes, add a new sanitized fixture and adjust the parser
with tests before changing production behavior.

## Data provenance and licenses

- **Operator status and station names:** [THEMA / Thessaloniki Metro](https://www.thessmetro.gr/)
- **Station positions:** original Trackr points plus additional coordinates
  taken from OpenStreetMap-derived station information at
  [Thessaloniki Metro Map](https://thessalonikimetro.org/en/metro-map/)
  and [network guide](https://thessalonikimetro.org/en/metro-line/).
  Station coordinates © OpenStreetMap contributors, [ODbL](https://opendatacommons.org/licenses/odbl/1-0/).
- **Application:** [MIT License](LICENSE), original copyright retained.

Stations and approximate positions should be periodically reviewed against
current published information. Branch statuses, like all other status values,
are derived only from the operator's current indicators.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md),
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [SECURITY.md](SECURITY.md).
