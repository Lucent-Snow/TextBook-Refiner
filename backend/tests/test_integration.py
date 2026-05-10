from backend.processing.integration import _cosine_sim


def test_cosine_similarity_uses_math_before_returning():
    assert _cosine_sim([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert _cosine_sim([1.0, 0.0], [0.0, 1.0]) == 0.0
