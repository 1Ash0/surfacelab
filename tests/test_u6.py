"""U6 tests: similarity.normalize, cosine_similarity, similarity_matrix, bm25_scores.

All expected values hand-computed before writing assertions.
"""

import pytest

from surfacelab.similarity import (
    bm25_scores,
    cosine_similarity,
    normalize,
    similarity_matrix,
)

# ---------------------------------------------------------------------------
# normalize
# ---------------------------------------------------------------------------


def test_normalize_unit_vector_unchanged() -> None:
    # [1.0, 0.0] already has magnitude 1 — unchanged
    result = normalize([1.0, 0.0])
    assert result == pytest.approx([1.0, 0.0])


def test_normalize_produces_magnitude_one() -> None:
    import math

    result = normalize([3.0, 4.0])
    mag = math.sqrt(sum(x * x for x in result))
    assert mag == pytest.approx(1.0)


def test_normalize_direction_preserved() -> None:
    # [3, 4] normalized = [0.6, 0.8]
    result = normalize([3.0, 4.0])
    assert result == pytest.approx([0.6, 0.8])


def test_normalize_zero_vector_returns_zero() -> None:
    result = normalize([0.0, 0.0])
    assert result == pytest.approx([0.0, 0.0])


def test_normalize_pure() -> None:
    v = [3.0, 4.0]
    normalize(v)
    assert v == [3.0, 4.0]


# ---------------------------------------------------------------------------
# cosine_similarity — hand-computed
# ---------------------------------------------------------------------------


def test_cosine_similarity_non_normalized_vectors() -> None:
    # a=[3,4] mag=5, b=[4,3] mag=5; dot=24; cos=24/25=0.96
    assert cosine_similarity([3.0, 4.0], [4.0, 3.0]) == pytest.approx(0.96)


def test_cosine_similarity_orthogonal_vectors() -> None:
    # [1,0]·[0,1]=0 → cos=0.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_similarity_identical_vectors() -> None:
    # cos(a, a) = 1.0 for any non-zero vector
    assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)


def test_cosine_similarity_opposite_vectors() -> None:
    # [1,0] vs [-1,0]: dot=-1, mags=1 each → cos=-1.0
    assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


def test_cosine_similarity_scale_invariant() -> None:
    # scaling a vector should not change the angle
    a = [1.0, 0.0]
    b = [0.707, 0.707]
    assert cosine_similarity(a, b) == pytest.approx(cosine_similarity([2.0, 0.0], b))


def test_cosine_similarity_zero_vector_returns_zero() -> None:
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == pytest.approx(0.0)


def test_cosine_similarity_length_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="mismatch"):
        cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])


# ---------------------------------------------------------------------------
# similarity_matrix — hand-computed 3×3
# ---------------------------------------------------------------------------


def test_similarity_matrix_3x3() -> None:
    # embeddings: [1,0], [0,1], [1,0]
    # (0,0)=1, (1,1)=1, (2,2)=1  (self-similarity)
    # (0,1)=0, (1,2)=0            (orthogonal)
    # (0,2)=1, (2,0)=1            (identical vectors)
    embeddings = [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]
    expected = [
        [1.0, 0.0, 1.0],
        [0.0, 1.0, 0.0],
        [1.0, 0.0, 1.0],
    ]
    actual = similarity_matrix(embeddings)
    for actual_row, expected_row in zip(actual, expected):
        assert actual_row == pytest.approx(expected_row)


def test_similarity_matrix_diagonal_is_one() -> None:
    embeddings = [[1.0, 0.0], [0.5, 0.5], [0.0, 1.0]]
    mat = similarity_matrix(embeddings)
    for i in range(3):
        assert mat[i][i] == pytest.approx(1.0)


def test_similarity_matrix_is_symmetric() -> None:
    embeddings = [[1.0, 0.0], [0.6, 0.8], [0.0, 1.0]]
    mat = similarity_matrix(embeddings)
    n = len(mat)
    for i in range(n):
        for j in range(n):
            assert mat[i][j] == pytest.approx(mat[j][i])


def test_similarity_matrix_values_in_range() -> None:
    embeddings = [[1.0, 0.0], [-1.0, 0.0], [0.0, 1.0]]
    mat = similarity_matrix(embeddings)
    for row in mat:
        for val in row:
            assert -1.0 - 1e-9 <= val <= 1.0 + 1e-9


def test_similarity_matrix_works_on_non_normalized_input() -> None:
    # [3,0] and [0,4] are not unit vectors but should give cos=0.0
    mat = similarity_matrix([[3.0, 0.0], [0.0, 4.0]])
    assert mat[0][1] == pytest.approx(0.0)
    assert mat[0][0] == pytest.approx(1.0)


def test_similarity_matrix_single_embedding() -> None:
    mat = similarity_matrix([[1.0, 0.0]])
    assert mat == [[pytest.approx(1.0)]]


# ---------------------------------------------------------------------------
# bm25_scores — ranking and boundary behaviour
# ---------------------------------------------------------------------------

_DESCS = [
    "Retrieve current weather conditions.",
    "List files in a directory.",
]


def test_bm25_weather_query_ranks_weather_tool_first() -> None:
    scores = bm25_scores(_DESCS, "Check the weather.")
    assert scores[0] > scores[1]


def test_bm25_file_query_ranks_file_tool_first() -> None:
    scores = bm25_scores(_DESCS, "Show me the files in a folder.")
    assert scores[1] > scores[0]


def test_bm25_empty_query_returns_all_zeros() -> None:
    scores = bm25_scores(_DESCS, "")
    assert scores == pytest.approx([0.0, 0.0])


def test_bm25_no_matching_terms_returns_zeros() -> None:
    # query terms ("quantum", "flux") appear in neither description
    scores = bm25_scores(_DESCS, "quantum flux")
    assert scores == pytest.approx([0.0, 0.0])


def test_bm25_returns_one_score_per_description() -> None:
    scores = bm25_scores(_DESCS, "weather")
    assert len(scores) == len(_DESCS)


def test_bm25_scores_are_nonnegative() -> None:
    scores = bm25_scores(_DESCS, "Check the weather.")
    assert all(s >= 0.0 for s in scores)


def test_bm25_deterministic() -> None:
    s1 = bm25_scores(_DESCS, "Check the weather.")
    s2 = bm25_scores(_DESCS, "Check the weather.")
    assert s1 == pytest.approx(s2)


def test_bm25_rare_term_scores_high() -> None:
    # "xyzzy" appears only in the first description — rare, high IDF
    descs = [
        "Retrieve xyzzy data from the remote endpoint.",
        "List files in a directory.",
        "Fetch the current temperature reading.",
    ]
    scores = bm25_scores(descs, "xyzzy")
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]


def test_bm25_term_in_every_doc_gets_low_idf() -> None:
    # "retrieve" appears in all three — IDF near log(1)=0; "xyzzy" is rare
    descs = [
        "Retrieve xyzzy data.",
        "Retrieve weather data.",
        "Retrieve file data.",
    ]
    scores_rare = bm25_scores(descs, "xyzzy")
    scores_common = bm25_scores(descs, "retrieve")
    # xyzzy only matches descs[0]; retrieve matches all — descs[0] should win for xyzzy
    assert scores_rare[0] > scores_rare[1]
    # retrieve is in all docs; all scores should be positive
    assert all(s > 0.0 for s in scores_common)


def test_bm25_empty_corpus_returns_empty() -> None:
    assert bm25_scores([], "weather") == []
