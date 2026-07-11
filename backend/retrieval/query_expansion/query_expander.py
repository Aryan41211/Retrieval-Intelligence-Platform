from __future__ import annotations

import re
import string
from dataclasses import dataclass
from typing import Any

from backend.configs.settings import QueryExpansionSettings

_WORD_RE = re.compile(r"\b\w+\b")


@dataclass
class ExpandedQuery:
    original: str
    normalized: str
    expanded: str
    synonyms_applied: list[dict[str, Any]]


class QueryExpander:
    """Lightweight query expansion (no LLM dependency).

    - query normalization (lowercase, whitespace cleanup)
    - synonym expansion using a provided mapping
    - punctuation cleanup
    - stop-word handling via a small builtin list (config-driven)
    """

    def __init__(self, *, settings: QueryExpansionSettings):
        self._settings = settings
        self._stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "if",
            "then",
            "else",
            "of",
            "to",
            "in",
            "on",
            "for",
            "with",
            "at",
            "by",
            "from",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "it",
            "this",
            "that",
            "as",
            "into",
            "about",
        }

    def expand(self, query_text: str) -> tuple[str, dict[str, Any]]:
        settings = self._settings
        original = query_text or ""
        normalized = self._normalize(original)

        if not settings.enabled:
            return normalized, {"enabled": False}

        expanded_text = normalized
        synonyms_applied: list[dict[str, Any]] = []

        if settings.synonyms_enabled:
            expanded_text, synonyms_applied = self._apply_synonyms(expanded_text)

        if settings.stopword_cleanup:
            expanded_text = self._remove_stopwords(expanded_text)

        if settings.punctuation_cleanup:
            expanded_text = self._cleanup_punctuation(expanded_text)

        return expanded_text.strip(), {
            "enabled": True,
            "original": original,
            "normalized": normalized,
            "synonyms_applied": synonyms_applied,
        }

    def _normalize(self, text: str) -> str:
        s = text or ""
        s = s.replace("\u00a0", " ")  # nbsp
        s = " ".join(s.split())
        if self._settings.lowercase:
            s = s.lower()
        return s

    def _apply_synonyms(self, text: str) -> tuple[str, list[dict[str, Any]]]:
        if not text:
            return text, []

        tokens = (
            _WORD_RE.findall(text.lower()) if self._settings.lowercase else _WORD_RE.findall(text)
        )
        token_set = set(tokens)

        synonyms_applied: list[dict[str, Any]] = []
        expanded_terms: list[str] = [text]

        for key, syns in (self._settings.synonyms or {}).items():
            if key in token_set:
                expanded_terms.append(" ".join(syns))
                synonyms_applied.append({"term": key, "synonyms": syns})

        # Ensure deterministic output
        expanded_text = " ".join(expanded_terms)
        expanded_text = " ".join(expanded_text.split())
        return expanded_text, synonyms_applied

    def _remove_stopwords(self, text: str) -> str:
        toks = _WORD_RE.findall(text.lower())
        kept = [t for t in toks if t not in self._stopwords]
        # Keep original ordering by re-joining tokens
        return " ".join(kept)

    def _cleanup_punctuation(self, text: str) -> str:
        # Replace punctuation with spaces; keep alphanumerics + whitespace.
        allowed = set(string.ascii_letters + string.digits + " ")
        cleaned = []
        for ch in text:
            if ch in allowed:
                cleaned.append(ch)
            else:
                cleaned.append(" ")
        return " ".join("".join(cleaned).split())
