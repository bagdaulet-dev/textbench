"""Bound JSON input before deserializing it, including streams without a length."""

from io import BytesIO

from django.conf import settings
from rest_framework.exceptions import APIException, ParseError
from rest_framework.parsers import JSONParser


class PayloadTooLarge(APIException):
    status_code = 413
    default_detail = "The request is too large. Send at most 256 KB of JSON."
    default_code = "payload_too_large"


class BoundedJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        body = stream.read(settings.DATA_UPLOAD_MAX_MEMORY_SIZE + 1)
        if len(body) > settings.DATA_UPLOAD_MAX_MEMORY_SIZE:
            raise PayloadTooLarge()
        try:
            return super().parse(BytesIO(body), media_type, parser_context)
        except RecursionError as exc:
            raise ParseError("The JSON structure is too deeply nested.") from exc
