from app.services.coherence import topic_coherence_status


def test_aligned_when_same_polar_stance():
    assert topic_coherence_status(["pour"], ["pour"]) == "aligned"


def test_conflict_when_opposite_polarities():
    assert topic_coherence_status(["pour"], ["contre"]) == "conflict"
    assert topic_coherence_status(["contre", "nuance"], ["pour"]) == "conflict"


def test_mixed_when_both_sides_present():
    assert topic_coherence_status(["pour", "contre"], ["pour"]) == "mixed"
    assert topic_coherence_status(["pour"], ["pour", "contre"]) == "mixed"


def test_claims_or_votes_only():
    assert topic_coherence_status(["pour"], []) == "claims_only"
    assert topic_coherence_status([], ["contre"]) == "votes_only"
    assert topic_coherence_status([], []) == "empty"


def test_abstention_and_nuance_without_polar():
    assert topic_coherence_status(["nuance"], ["abstention"]) == "abstention_only"


def test_topics_yaml_seed_shape():
    from pathlib import Path

    import yaml

    path = Path(__file__).resolve().parents[1] / "seeds" / "topics.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    topics = data["topics"]
    assert len(topics) >= 10
    slugs = {t["slug"] for t in topics}
    assert "immigration" in slugs
    assert "fiscalite" in slugs
    for topic in topics:
        assert topic["slug"]
        assert topic["label"]
        assert isinstance(topic.get("sort_order", 0), int)
