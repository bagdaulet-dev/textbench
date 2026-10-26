from io import BytesIO

import pytest
from rest_framework.exceptions import ParseError
from text_tools.parsers import BoundedJSONParser, PayloadTooLarge


@pytest.mark.parametrize("length_header", [None, "1", "999999"])
def test_body_limit_does_not_trust_declared_length(length_header, settings):
    settings.DATA_UPLOAD_MAX_MEMORY_SIZE = 32
    stream = BytesIO(b'{"text":"' + b"x" * 1000 + b'"}')
    with pytest.raises(PayloadTooLarge):
        BoundedJSONParser().parse(stream, parser_context={"content_length": length_header})
    assert stream.tell() == 33


def test_parser_accepts_valid_unicode():
    body = '{"text":"Сәлем 👋"}'.encode()
    assert BoundedJSONParser().parse(BytesIO(body)) == {"text": "Сәлем 👋"}


def test_parser_rejects_invalid_json():
    with pytest.raises(ParseError):
        BoundedJSONParser().parse(BytesIO(b"{"))
