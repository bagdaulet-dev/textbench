import json
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.db import DatabaseError
from django.utils import timezone
from rest_framework.test import APIClient
from text_tools.models import TextAnalysis

pytestmark = pytest.mark.django_db


def save_analysis(client, text="A clear idea. A useful sentence."):
    response = client.post("/api/text/analyze/", {"text": text, "save": True}, format="json")
    assert response.status_code == 200, response.content
    return response.json()


def test_analyze_without_saving(client):
    response = client.post("/api/text/analyze/", {"text": "Hello world!"}, format="json")
    assert response.status_code == 200
    assert response.json()["result"]["word_count"] == 2
    assert response.json()["saved"] is False
    assert response.json()["id"] is None
    assert TextAnalysis.objects.count() == 0
    assert "sessionid" not in response.cookies
    assert response["Cache-Control"] == "no-store"


def test_save_and_restore_history(client):
    saved = save_analysis(client)
    assert saved["saved"] is True
    assert TextAnalysis.objects.count() == 1
    response = client.get("/api/text/history/")
    assert response.status_code == 200
    assert response.json()["count"] == 1
    record = response.json()["results"][0]
    assert record["id"] == saved["id"]
    assert "session_key" not in record
    detail = client.get(f"/api/text/history/{saved['id']}/")
    assert detail.json()["text"] == "A clear idea. A useful sentence."
    assert str(TextAnalysis.objects.get(pk=saved["id"])) == f"Analysis {saved['id']}"


def test_browser_sessions_cannot_access_each_others_history(client):
    saved = save_analysis(client)
    other = APIClient()
    assert other.get("/api/text/history/").json()["count"] == 0
    assert other.get(f"/api/text/history/{saved['id']}/").status_code == 404
    assert other.delete(f"/api/text/history/{saved['id']}/").status_code == 404
    assert TextAnalysis.objects.count() == 1
    save_analysis(other, "Separate browser")
    assert client.get("/api/text/history/").json()["count"] == 1
    assert other.get("/api/text/history/").json()["count"] == 1


def test_delete_saved_analysis(client):
    saved = save_analysis(client)
    response = client.delete(f"/api/text/history/{saved['id']}/")
    assert response.status_code == 204
    assert response["Cache-Control"] == "no-store"
    assert TextAnalysis.objects.count() == 0
    assert client.delete(f"/api/text/history/{saved['id']}/").status_code == 404


def test_history_pagination_newest_first(client):
    ids = [save_analysis(client, f"Draft {i}")["id"] for i in range(7)]
    first_page = client.get("/api/text/history/").json()
    assert first_page["count"] == 7
    assert len(first_page["results"]) == 6
    assert first_page["results"][0]["id"] == ids[-1]
    assert first_page["next"] is not None
    second_page = client.get("/api/text/history/?page=2").json()
    assert second_page["results"][0]["id"] == ids[0]


@pytest.mark.parametrize("text", ["", "   \n\t", "x" * 20_001, None])
def test_invalid_input_is_rejected(client, text):
    response = client.post("/api/text/analyze/", {"text": text, "save": True}, format="json")
    assert response.status_code == 400
    assert "text" in response.json()
    assert TextAnalysis.objects.count() == 0


def test_missing_text_and_invalid_save_flag(client):
    assert client.post("/api/text/analyze/", {}, format="json").status_code == 400
    response = client.post("/api/text/analyze/", {"text": "text", "save": "maybe"}, format="json")
    assert response.status_code == 400


def test_maximum_length_is_accepted(client):
    response = client.post("/api/text/analyze/", {"text": "x" * 20_000}, format="json")
    assert response.status_code == 200
    assert response.json()["result"]["character_count"] == 20_000


def test_unicode_round_trip_uses_database(client):
    text = "Сәлем, әлем! Café 👩🏽‍💻 你好"
    saved = save_analysis(client, text)
    assert client.get(f"/api/text/history/{saved['id']}/").json()["text"] == text


def test_transformation_does_not_save_history(client):
    response = client.post(
        "/api/text/transform/", {"text": "My first API!", "operation": "slug"}, format="json"
    )
    assert response.status_code == 200
    assert response.json() == {"operation": "slug", "result": "my-first-api"}
    assert response["Cache-Control"] == "no-store"
    assert TextAnalysis.objects.count() == 0
    invalid = client.post(
        "/api/text/transform/", {"text": "hello", "operation": "invalid"}, format="json"
    )
    assert invalid.status_code == 400


def test_csrf_required_even_without_login():
    browser = APIClient(enforce_csrf_checks=True)
    assert browser.post("/api/text/analyze/", {"text": "hello"}, format="json").status_code == 403
    response = browser.get("/api/csrf/")
    token = response.json()["csrfToken"]
    saved = browser.post(
        "/api/text/analyze/", {"text": "hello", "save": True}, format="json", HTTP_X_CSRFTOKEN=token
    )
    assert saved.status_code == 200
    record_id = saved.json()["id"]
    assert browser.delete(f"/api/text/history/{record_id}/").status_code == 403
    assert (
        browser.delete(f"/api/text/history/{record_id}/", HTTP_X_CSRFTOKEN=token).status_code == 204
    )


def test_methods_and_content_types(client):
    assert client.get("/api/text/analyze/").status_code == 405
    assert client.post("/api/text/history/", {}, format="json").status_code == 405
    assert client.post("/api/text/analyze/", "bad", content_type="text/plain").status_code == 415


def test_health_checks_database(client):
    assert client.get("/api/health/").json() == {"status": "ok", "database": "ok"}
    with patch("text_tools.views.connection.cursor", side_effect=DatabaseError("private details")):
        response = client.get("/api/health/")
    assert response.status_code == 503
    assert "private details" not in response.content.decode()


def test_database_failure_returns_safe_error(client):
    save_analysis(client)
    with patch("text_tools.views.TextAnalysis.objects.create", side_effect=DatabaseError("secret")):
        response = client.post("/api/text/analyze/", {"text": "hello", "save": True}, format="json")
    assert response.status_code == 503
    assert response.json()["detail"] == "The database is unavailable. Please try again shortly."


def test_frontend_and_api_docs_are_served(client, settings):
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    response = client.get("/")
    assert response.status_code == 200
    assert b"text-input" in response.content
    assert "csrftoken" in response.cookies
    assert client.get("/api/docs/").status_code == 200
    assert client.get("/api/schema/").status_code == 200


def test_expired_sessions_cannot_read_saved_text(client):
    save_analysis(client)
    Session.objects.filter(session_key=client.session.session_key).update(
        expire_date=timezone.now() - timedelta(days=1)
    )
    assert client.get("/api/text/history/").json()["count"] == 0


def test_saving_after_expiry_creates_a_new_session(client):
    old_id = save_analysis(client)["id"]
    old_key = client.session.session_key
    Session.objects.filter(session_key=old_key).update(
        expire_date=timezone.now() - timedelta(days=1)
    )
    new_id = save_analysis(client, "New session text")["id"]
    assert client.session.session_key != old_key
    assert client.get(f"/api/text/history/{old_id}/").status_code == 404
    assert client.get(f"/api/text/history/{new_id}/").status_code == 200


def test_cleanup_retains_active_history_and_removes_expired(client):
    active = save_analysis(client)["id"]
    expired_client = APIClient()
    expired = save_analysis(expired_client)["id"]
    Session.objects.filter(session_key=expired_client.session.session_key).update(
        expire_date=timezone.now() - timedelta(days=1)
    )
    TextAnalysis.objects.create(session_key="deleted-session", text="orphan", result={})
    output = StringIO()
    call_command("purge_expired_analyses", stdout=output)
    assert TextAnalysis.objects.filter(pk=active).exists()
    assert not TextAnalysis.objects.filter(pk=expired).exists()
    assert TextAnalysis.objects.count() == 1
    assert "Deleted 2" in output.getvalue()


@pytest.mark.parametrize("text", [123, 1.5, True, [], {}, "\ud800"])
def test_text_requires_a_valid_unicode_string(client, text):
    # Encode malformed Unicode as JSON escapes so it reaches the server parser.
    response = client.post(
        "/api/text/analyze/", json.dumps({"text": text}), content_type="application/json"
    )
    assert response.status_code == 400
    assert "text" in response.json()


def test_json_size_is_bounded_before_validation(client):
    response = client.post("/api/text/analyze/", {"text": "x" * 300_000}, format="json")
    assert response.status_code == 413
    assert response["Cache-Control"] == "no-store"
    assert TextAnalysis.objects.count() == 0


def test_deeply_nested_json_returns_a_client_error(client):
    response = client.post(
        "/api/text/analyze/", "[" * 1500 + "0" + "]" * 1500, content_type="application/json"
    )
    assert response.status_code == 400


def test_history_search_is_session_scoped_and_bounded(client):
    wanted = save_analysis(client, "A Python backend draft")["id"]
    save_analysis(client, "A Java draft")
    other = APIClient()
    save_analysis(other, "Private Python draft")
    response = client.get("/api/text/history/", {"search": "python"})
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["id"] == wanted
    assert client.get("/api/text/history/", {"search": "no match"}).json()["count"] == 0
    assert client.get("/api/text/history/", {"search": "a" * 101}).status_code == 400


def test_bulk_delete_clears_only_own_records_even_with_a_search(client):
    save_analysis(client, "First draft")
    save_analysis(client, "Second draft")
    other = APIClient()
    private_id = save_analysis(other, "Keep this draft")["id"]
    response = client.delete("/api/text/history/?search=First&page=2")
    assert response.status_code == 204
    assert client.get("/api/text/history/").json()["count"] == 0
    assert other.get(f"/api/text/history/{private_id}/").status_code == 200
    assert TextAnalysis.objects.count() == 1


def test_bulk_delete_requires_csrf_and_accepts_a_valid_token():
    browser = APIClient(enforce_csrf_checks=True)
    token = browser.get("/api/csrf/").json()["csrfToken"]
    browser.post(
        "/api/text/analyze/", {"text": "keep", "save": True}, format="json", HTTP_X_CSRFTOKEN=token
    )
    assert browser.delete("/api/text/history/").status_code == 403
    assert TextAnalysis.objects.count() == 1
    assert browser.delete("/api/text/history/", HTTP_X_CSRFTOKEN=token).status_code == 204
    assert TextAnalysis.objects.count() == 0


def test_expired_session_cannot_bulk_delete_old_records(client):
    record = save_analysis(client)["id"]
    Session.objects.filter(session_key=client.session.session_key).update(
        expire_date=timezone.now() - timedelta(days=1)
    )
    assert client.delete("/api/text/history/").status_code == 204
    assert TextAnalysis.objects.filter(pk=record).exists()


def test_security_headers_cover_success_and_error_responses(client):
    for response in [
        client.get("/api/csrf/"),
        client.get("/api/text/history/999999/"),
        client.post("/api/text/analyze/", {}, format="json"),
    ]:
        assert "script-src 'self'" in response["Content-Security-Policy"]
        assert "'unsafe-inline'" not in response["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in response["Content-Security-Policy"]
        assert "camera=()" in response["Permissions-Policy"]
        assert response["X-Content-Type-Options"] == "nosniff"
        assert response["Cache-Control"] == "no-store"


def test_documentation_can_be_disabled(client, settings):
    settings.ENABLE_API_DOCS = False
    assert client.get("/api/docs/").status_code == 404
    assert client.get("/api/schema/").status_code == 404
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    assert b'href="/api/docs/"' not in client.get("/").content
    settings.ENABLE_API_DOCS = True
    assert client.get("/api/docs/").status_code == 200


def test_throttled_requests_return_retry_after(client):
    from rest_framework.throttling import AnonRateThrottle
    from text_tools.views import AnalyzeView

    class OncePerMinute(AnonRateThrottle):
        rate = "1/min"

    with patch.object(AnalyzeView, "throttle_classes", [OncePerMinute]):
        assert (
            client.post("/api/text/analyze/", {"text": "hello"}, format="json").status_code == 200
        )
        blocked = client.post("/api/text/analyze/", {"text": "hello"}, format="json")
    assert blocked.status_code == 429
    assert "Retry-After" in blocked
    assert blocked["Cache-Control"] == "no-store"
