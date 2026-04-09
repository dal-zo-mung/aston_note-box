from __future__ import annotations

import re


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "should",
    "so",
    "that",
    "the",
    "their",
    "them",
    "this",
    "to",
    "use",
    "want",
    "was",
    "we",
    "with",
    "you",
    "your",
}


def normalize_keywords(keyword_text: str) -> list[str]:
    seen: set[str] = set()
    keywords: list[str] = []

    for raw in re.split(r"[^A-Za-z0-9]+", keyword_text.lower()):
        token = raw.strip()
        if len(token) < 2 or token in STOPWORDS or token in seen:
            continue
        seen.add(token)
        keywords.append(token)

    return keywords


def extract_keywords(content: str, *, fallback: list[str] | None = None) -> list[str]:
    keywords = normalize_keywords(content)
    if keywords:
        return keywords[:5]

    if fallback:
        return normalize_keywords(" ".join(fallback))[:5]

    return []
