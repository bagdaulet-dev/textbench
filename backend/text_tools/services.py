"""Pure text functions: no HTTP requests or database access here."""

import math
import re
from collections import Counter

from django.utils.text import slugify

WORD_PATTERN = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)
OPERATIONS = ("uppercase", "lowercase", "titlecase", "slug", "compact_whitespace")


def analyze_text(text):
    words = WORD_PATTERN.findall(text)
    normalized = [word.casefold().replace("’", "'") for word in words]
    frequencies = Counter(normalized)
    # This deliberately simple rule is documented; it is not a language model.
    sentences = [part for part in re.split(r"[.!?]+", text) if WORD_PATTERN.search(part)]
    return {
        "word_count": len(words),
        "character_count": len(text),
        "characters_without_whitespace": sum(not c.isspace() for c in text),
        "sentence_count": len(sentences),
        "paragraph_count": len([p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]),
        "unique_word_count": len(frequencies),
        "reading_time_seconds": math.ceil(len(words) * 60 / 200),
        "top_words": [{"word": word, "count": count} for word, count in frequencies.most_common(8)],
    }


def transform_text(text, operation):
    transforms = {
        "uppercase": str.upper,
        "lowercase": str.lower,
        "titlecase": str.title,
        "slug": slugify,
        "compact_whitespace": lambda value: " ".join(value.split()),
    }
    if operation not in transforms:
        raise ValueError("Unsupported text operation.")
    return transforms[operation](text)
