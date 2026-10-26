import pytest
from text_tools.services import analyze_text, transform_text


def test_analysis_counts_a_real_paragraph():
    result = analyze_text("Hello, world! Hello again.\n\nA new paragraph?")
    assert result["word_count"] == 7
    assert result["sentence_count"] == 3
    assert result["paragraph_count"] == 2
    assert result["unique_word_count"] == 6
    assert result["top_words"][0] == {"word": "hello", "count": 2}
    assert result["reading_time_seconds"] == 3


def test_unicode_apostrophes_and_hyphens():
    result = analyze_text("Café CAFÉ don't don’t well-known 2026 қазақша")
    assert result["word_count"] == 7
    assert result["unique_word_count"] == 5
    assert result["top_words"][:2] == [{"word": "café", "count": 2}, {"word": "don't", "count": 2}]


def test_characters_include_unicode_and_whitespace():
    result = analyze_text("Hi 👋\nthere\t!")
    assert result["character_count"] == len("Hi 👋\nthere\t!")
    assert result["characters_without_whitespace"] == len("Hi👋there!")


def test_sentence_rules_count_unterminated_text():
    assert analyze_text("First!Second? Third without a stop")["sentence_count"] == 3
    assert analyze_text("...?! 👋")["sentence_count"] == 0


def test_empty_text_function_is_defined():
    result = analyze_text("")
    assert result["word_count"] == result["paragraph_count"] == 0
    assert result["reading_time_seconds"] == 0
    assert result["top_words"] == []


def test_reading_time_and_frequency_limit():
    assert analyze_text("word " * 201)["reading_time_seconds"] == 61
    assert len(analyze_text("one two three four five six seven eight nine ten")["top_words"]) == 8


@pytest.mark.parametrize(
    ("operation", "source", "expected"),
    [
        ("uppercase", "Hello café", "HELLO CAFÉ"),
        ("lowercase", "Hello WORLD", "hello world"),
        ("titlecase", "a simple title", "A Simple Title"),
        ("slug", "Café & Python: a guide!", "cafe-python-a-guide"),
        ("slug", "你好", ""),
        ("compact_whitespace", "  a\t b\n\n c  ", "a b c"),
    ],
)
def test_transformations(operation, source, expected):
    assert transform_text(source, operation) == expected


def test_unknown_operation_is_rejected():
    with pytest.raises(ValueError, match="Unsupported"):
        transform_text("hello", "execute_code")
