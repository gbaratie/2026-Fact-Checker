from app.utils.text import candidate_mentioned, normalize_text


def test_normalize_text():
    assert normalize_text("François Ruffin") == "francois ruffin"


def test_candidate_mentioned_full_name():
    assert candidate_mentioned("Marine Le Pen annonce sa candidature", "Marine Le Pen")


def test_candidate_mentioned_last_name():
    assert candidate_mentioned("Ruffin critique le gouvernement", "François Ruffin")


def test_candidate_not_mentioned():
    assert not candidate_mentioned("Le budget est adopté", "Marine Le Pen")
