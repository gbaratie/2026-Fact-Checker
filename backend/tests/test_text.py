from app.utils.text import candidate_mentioned, normalize_text, slugify


def test_normalize_text():
    assert normalize_text("François Ruffin") == "francois ruffin"


def test_slugify():
    assert slugify("Gabriel Attal") == "gabriel-attal"
    assert slugify("  Marine Le Pen ") == "marine-le-pen"
    assert slugify("Jean-Luc Mélenchon") == "jean-luc-melenchon"


def test_candidate_mentioned_full_name():
    assert candidate_mentioned("Marine Le Pen annonce sa candidature", "Marine Le Pen")


def test_candidate_mentioned_last_name():
    assert candidate_mentioned("Ruffin critique le gouvernement", "François Ruffin")


def test_candidate_mentioned_compound_last_name():
    assert candidate_mentioned("Le Pen refuse le débat", "Marine Le Pen")


def test_candidate_not_mentioned():
    assert not candidate_mentioned("Le budget est adopté", "Marine Le Pen")


def test_candidate_not_mentioned_substring_false_positive():
    assert not candidate_mentioned(
        "Vanuatu prêt à porter son différend avec la France",
        "Marine Le Pen",
    )
    assert not candidate_mentioned(
        "Le président dépend du Parlement",
        "Marine Le Pen",
    )
