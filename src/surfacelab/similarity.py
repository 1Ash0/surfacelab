"""Embedding-based and lexical similarity utilities.

All functions are pure and work on pre-loaded vectors — no API calls here.
Embedding generation lives in scripts/; UMAP export lives in scripts/.

U6 public API
-------------
normalize            -- L2-normalize a vector
cosine_similarity    -- single-pair cosine similarity
similarity_matrix    -- NxN cosine similarity matrix for N embeddings
bm25_scores          -- BM25 lexical scores of descriptions against a query
"""

from __future__ import annotations

import math
import re
from collections import Counter


def normalize(v: list[float]) -> list[float]:
    """L2-normalize v. Returns zero vector unchanged (avoids division by zero)."""
    mag = math.sqrt(sum(x * x for x in v))
    if mag == 0.0:
        return list(v)
    return [x / mag for x in v]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. Vectors need not be pre-normalized.

    Returns 0.0 if either vector is the zero vector.
    Raises ValueError for mismatched lengths.
    """
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


def similarity_matrix(embeddings: list[list[float]]) -> list[list[float]]:
    """Return NxN cosine similarity matrix for N embedding vectors.

    Pre-normalizes each vector once (not N² times). The diagonal is 1.0;
    off-diagonal entry (i,j) is the cosine similarity of tools i and j.
    """
    norms = [normalize(e) for e in embeddings]
    n = len(norms)
    return [
        [sum(a * b for a, b in zip(norms[i], norms[j])) for j in range(n)]
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# BM25 lexical scorer
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens."""
    return re.findall(r'[a-z0-9]+', text.lower())


def bm25_scores(
    descriptions: list[str],
    query: str,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    """BM25 score of each description against query.

    Higher score = better keyword match. Scores are non-negative.
    Empty query or no matching terms returns 0.0 for every description.

    Parameters
    ----------
    descriptions : tool descriptions — the BM25 corpus
    query        : request text to score against
    k1           : term-frequency saturation (default 1.5)
    b            : document-length normalisation (default 0.75)

    IDF formula: log((N - df + 0.5) / (df + 0.5) + 1)
    The +1 ensures IDF >= 0 even when a term appears in every document.
    """
    docs = [_tokenize(d) for d in descriptions]
    n = len(docs)
    if n == 0:
        return []

    avgdl = sum(len(d) for d in docs) / n

    df: Counter[str] = Counter()
    for doc in docs:
        for term in set(doc):
            df[term] += 1

    q_terms = _tokenize(query)
    scores: list[float] = []
    for doc in docs:
        tf = Counter(doc)
        dl = len(doc)
        score = 0.0
        for term in q_terms:
            if term not in tf:
                continue
            f = tf[term]
            idf = math.log((n - df[term] + 0.5) / (df[term] + 0.5) + 1)
            tf_norm = f * (k1 + 1) / (f + k1 * (1 - b + b * dl / avgdl))
            score += idf * tf_norm
        scores.append(score)

    return scores
