# Verification record

Verified on 26 October 2026 from the project in Downloads/projects_for_github.

## Automated checks

- 54 tests passed against a real MySQL 8.4 container using a separate test database.
- Application package line coverage: 99.6%; migrations are excluded.
- The isolated fallback suite also passed.
- Ruff, JavaScript syntax, frontend formatting, and OpenAPI validation passed.
- The Docker image built, and both app and MySQL containers reported healthy.
- Dependency checks reported no known advisories for the pinned Python
  requirements and the development-only Node packages after the framework update.

An independent reviewer confirmed the original concrete security findings were
addressed. A temporary copy was used to remove the session ownership filter:
normal cross-browser tests passed first, and both then failed under the mutation.
The original project was never mutated for this experiment.

## Repeatable browser checks

`scripts/browser-smoke.mjs` ran successfully in an isolated Chrome profile:

- Inline validation and undo after draft replacement/clearing.
- Local UTF-8 import, invalid-file rejection, and Unicode character counting.
- Saving, searching, restoring, and disabling bulk deletion during a pending save.
- All five transformations, text download, Ctrl/Command+Enter analysis, and
  current-analysis JSON export; editing invalidates export.
- Oversized uppercase output leaves the original draft intact.
- Canceling bulk deletion preserves history; confirmation clears every owned
  record even while a search hides some of them.
- Desktop 1440px and mobile 390px; no horizontal mobile overflow.
- No JavaScript or browser console errors during the automated journey.

The script writes desktop and mobile screenshots using only synthetic example
text. Run it with `npm run test:browser`, or use `BROWSER_CHANNEL=chrome` with an
existing Chrome installation. CI installs its own Chromium and runs the same test.

## External boundaries

The README links to the current GitHub Actions results. Production HTTPS/SSH
deployment requires the server, domain, and environment credentials described
in deployment.md. Coverage and advisory scans are evidence for the documented
checks, not a guarantee that all possible faults have been found.
