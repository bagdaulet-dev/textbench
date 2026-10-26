from django.core.exceptions import RequestDataTooBig
from django.db import DatabaseError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    if isinstance(exc, RequestDataTooBig):
        return Response(
            {"detail": "The request is too large. Send at most 256 KB of JSON."}, status=413
        )
    if isinstance(exc, DatabaseError):
        return Response(
            {"detail": "The database is unavailable. Please try again shortly."}, status=503
        )
    return exception_handler(exc, context)
