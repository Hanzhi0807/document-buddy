from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SearchDocument:
    doc_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def tokenize_search_text(text: str) -> list[str]:
    lowered = text.lower()
    tokens = [token for token in re.findall(r"[a-z0-9][a-z0-9._-]*", lowered) if len(token) > 1]
    for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", lowered):
        if len(chunk) <= 8:
            tokens.append(chunk)
        for size in (2, 3):
            for idx in range(0, len(chunk) - size + 1):
                tokens.append(chunk[idx : idx + size])
    return tokens


def rank_bm25(
    query: str,
    documents: list[SearchDocument],
    top_k: int | None = None,
    *,
    include_zero: bool = False,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[tuple[SearchDocument, float]]:
    query_terms = tokenize_search_text(query)
    if not query_terms or not documents:
        if include_zero:
            limit = top_k or len(documents)
            return [(document, 0.0) for document in documents[:limit]]
        return []

    doc_term_counts = [Counter(tokenize_search_text(document.text)) for document in documents]
    doc_lengths = [sum(counts.values()) for counts in doc_term_counts]
    avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0.0
    if avg_doc_length <= 0:
        if include_zero:
            limit = top_k or len(documents)
            return [(document, 0.0) for document in documents[:limit]]
        return []

    document_frequency: Counter[str] = Counter()
    for counts in doc_term_counts:
        document_frequency.update(counts.keys())

    total_docs = len(documents)
    query_counts = Counter(query_terms)
    scored: list[tuple[int, SearchDocument, float]] = []
    for idx, (document, counts, doc_length) in enumerate(
        zip(documents, doc_term_counts, doc_lengths)
    ):
        score = 0.0
        for term, query_count in query_counts.items():
            frequency = counts.get(term, 0)
            if frequency <= 0:
                continue
            df = document_frequency[term]
            idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
            denominator = frequency + k1 * (1 - b + b * doc_length / avg_doc_length)
            score += idf * query_count * (frequency * (k1 + 1) / denominator)
        if include_zero or score > 0:
            scored.append((idx, document, score))

    scored.sort(key=lambda item: (-item[2], item[0]))
    if top_k is not None:
        scored = scored[:top_k]
    return [(document, score) for _, document, score in scored]
