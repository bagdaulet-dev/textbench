# Security scope

Textbench uses anonymous browser sessions. It has no registered-user identities.
A valid session cookie grants access to that session’s saved text. Possession of
a copied cookie can grant the same access; never treat browser sessions as proof
of a person’s identity. Saved text is plain data in MySQL, not end-to-end encrypted.

## Implemented controls

- Every history query and delete filters by the validated, unexpired session.
- Foreign or nonexistent record IDs return 404. Bulk deletion stays scoped to
  the current session and ignores search/pagination only within that scope.
- Anonymous POST and DELETE requests require CSRF validation.
- Session cookies are HttpOnly and SameSite=Lax; production uses Secure cookies
  and HTTPS through the private Caddy-to-application topology.
- Text inputs are strict strings, valid Unicode, and at most 20,000 code points.
  JSON parsing is capped at 256,000 bytes, with a safe JSON 413 response.
- Django ORM parameterizes queries. The frontend renders submitted text through
  textContent/textarea values, rather than interpreting it as HTML.
- The workspace CSP permits its own scripts/styles and disables objects, frames,
  and foreign form destinations. Camera, microphone, and geolocation are disabled.
- Development Swagger has a separate policy permitting its CDN assets and inline
  initialization. Docs and schema are disabled by default in production.
- Workspace/API responses use no-store, including error responses.
- The web container receives only its needed settings and restricted MySQL
  password. The root database password remains in the database container.
- MySQL is private in production; local ports bind only to 127.0.0.1.
- Access logs omit query strings and request bodies. If you enable additional
  proxy or development logs, review their handling of search terms separately.
- Secrets, private keys, local environment variants, and dependency directories
  are excluded from Git. Runtime and development versions are pinned.

## Checks performed

54 Python tests passed against MySQL. They cover session separation/expiry, CSRF,
search, bulk deletion, validation, size limits, errors, security headers, docs
visibility, and throttling. An isolated mutation that removed the ownership
filter caused both cross-browser access and deletion tests to fail.

The dependency advisory scan found issues in the original REST Framework pin.
It was upgraded to 3.18.3 after reviewing the official release notes. A fresh
scan of the pinned Python requirements and npm packages reported no known
vulnerabilities on 26 October 2026. This checks published advisories, not every
possible vulnerability. CI repeats the checks.

## Operational boundaries

The single-process IP throttle is best effort, not a distributed quota or DDoS
service. Scaling requires a shared limiter and a review of the trusted-proxy
configuration. Keep the app port private when trusting forwarded headers.
Session expiry removes access immediately; running the cleanup commands removes
the stored expired data. Configure daily cleanup and backups on the deployment
server. Local development intentionally allows HTTP and debug behavior.

These controls and tests are an application review, not a penetration-test
certification or a determination of legal compliance.
