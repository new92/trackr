# Security policy

## Supported version

Trackr 3.x is the maintained line in this revised source tree. Earlier versions
should be upgraded; they may have unreliable status reporting and dependencies.

## Vulnerability reporting

Please **do not disclose vulnerabilities through a public issue or discussion**.
Use GitHub's private vulnerability reporting feature under the repository's
**Security** tab (if enabled). Otherwise contact the maintainer privately at
**new92github@gmail.com** (listed in the original project README) and include
steps to reproduce, affected versions and potential impact. Do not include
private location data, real credentials, or harmful payloads in public reports.

## Security properties and limits

- The application only scrapes the fixed official `https://www.thessmetro.gr/` URL.
- Outgoing HTTP requests have connection/read timeouts and a response-size cap.
- The browser's nearest-station feature computes locally; the legacy `/api/nearest`
  endpoint accepts coordinates, but the dashboard does not call it.
- Notifications are optional and only run while a dashboard tab is open.
- No accounts, cookies or tracking scripts are required.
- Source-derived text is rendered with autoescaping or `textContent`.
- Scraping HTML is inherently fragile; never rely on Trackr as the sole source of
  safety-critical transportation information. Confirm at the official operator.
