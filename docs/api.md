# API guide

Base URL in local development: `http://localhost:8000`. Trailing slashes are
required. Request and response bodies use JSON unless noted otherwise.

## Complete example using only Python's standard library

Run this after the application is running. One cookie jar is essential: it holds
both the CSRF cookie and the session cookie that owns saved history.

```python
import http.cookiejar
import json
import urllib.request

base = "http://localhost:8000"
cookies = http.cookiejar.CookieJar()
client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))

with client.open(base + "/api/csrf/") as response:
    token = json.load(response)["csrfToken"]


def request(path, method="GET", body=None):
    headers = {"Accept": "application/json", "X-CSRFToken": token}
    payload = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        payload = json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=payload, headers=headers, method=method)
    with client.open(req) as response:
        return None if response.status == 204 else json.load(response)


analysis = request(
    "/api/text/analyze/",
    "POST",
    {
        "text": "Hello world. Hello Python!",
        "save": True,
    },
)
print(analysis)
print(
    request(
        "/api/text/transform/",
        "POST",
        {
            "text": "My first Python API!",
            "operation": "slug",
        },
    )
)
print(request("/api/text/history/"))
request(f"/api/text/history/{analysis['id']}/", "DELETE")
```

## Analyze

`POST /api/text/analyze/`

```json
{"text": "Hello world. Hello Python!", "save": false}
```

`save` is optional and defaults to false. Input must contain non-whitespace text
and may contain at most 20,000 Unicode code points.

```json
{
  "id": null,
  "saved": false,
  "result": {
    "word_count": 4,
    "character_count": 26,
    "characters_without_whitespace": 23,
    "sentence_count": 2,
    "paragraph_count": 1,
    "unique_word_count": 3,
    "reading_time_seconds": 2,
    "top_words": [
      {"word": "hello", "count": 2},
      {"word": "world", "count": 1},
      {"word": "python", "count": 1}
    ]
  }
}
```

A saved response contains an integer ID and `"saved": true`. HTTP status is 200
for both saved and unsaved analyses. Saving the same text twice creates two
records; there is no deduplication or idempotency key in this version.

## Transform

`POST /api/text/transform/`

```json
{"text": "My first Python API!", "operation": "slug"}
```

```json
{"operation": "slug", "result": "my-first-python-api"}
```

Operations: `uppercase`, `lowercase`, `titlecase`, `slug`, `compact_whitespace`.
Transformations are never saved automatically. Move a result into the editor and
save a new analysis if you want to keep it.

## History

`GET /api/text/history/?page=1` returns six records per page, newest first.
Add `&search=python` to filter within this browser’s records. Search is optional,
case-insensitive under the configured MySQL collation, and limited to 100 characters:

```json
{"count": 0, "next": null, "previous": null, "results": []}
```

Each record has `id`, `text`, `result` (the same statistics object as above), and
`created_at` in ISO 8601 UTC format. The browser's session determines which
records are visible. With no session the result is an empty list.

`GET /api/text/history/{id}/` retrieves one record.

`DELETE /api/text/history/{id}/` deletes it and returns 204 with no body.

`DELETE /api/text/history/` deletes **all** records belonging to the current
browser session and returns 204. It intentionally ignores search and pagination.
It requires the same CSRF header as single-record deletion.

A foreign or nonexistent ID returns 404. An invalid page also returns 404.

## Errors

Examples:

```json
{"text": ["Enter some text first."]}
```

```json
{"detail": "The database is unavailable. Please try again shortly."}
```

Expected statuses include 400 (validation), 403 (CSRF), 404, 405, 413 (request too large), 415, 429
(throttling), and 503 (database unavailable). Analysis, transformation, and history
responses use `Cache-Control: no-store`.

## Interactive docs

Documentation is available when `DJANGO_ENABLE_API_DOCS=true`. It defaults to
the debug setting for a local Python process; the production Compose configuration
defaults it to false. Both `/api/docs/` and `/api/schema/` return 404 when disabled.
This visibility option is separate from data-access protection.

When enabled, open `/api/docs/`. First call `GET /api/csrf/`, copy its `csrfToken`, choose
**Authorize**, and enter that value for `csrfToken`. Keep the browser's cookie
jar intact. You can then try POST and DELETE endpoints. The Swagger interface
uses externally hosted Swagger assets; the main workspace does not.

## Payload limits

The JSON body is capped at 256,000 bytes. Oversized bodies return a generic JSON
413 response before deserialization; malformed JSON returns 400. The `text` value
must be an actual Unicode string rather than a number, list, boolean, or object.
Text itself is limited to 20,000 Unicode code points.
