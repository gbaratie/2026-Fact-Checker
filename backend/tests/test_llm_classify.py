"""Tests parsing LLM (pas d'appel réseau)."""

from app.services.llm_classify import (
    clamp_confidence,
    filter_topic_slugs,
    parse_program_claims,
    parse_vote_classification,
)

ALLOWED = {
    "immigration",
    "fiscalite",
    "energie-climat",
    "securite",
}


def test_filter_topic_slugs_keeps_allowed_and_caps():
    raw = ["immigration", "inconnu", "fiscalite", "immigration", "securite"]
    assert filter_topic_slugs(raw, ALLOWED, max_topics=2) == ["immigration", "fiscalite"]


def test_filter_topic_slugs_rejects_non_list():
    assert filter_topic_slugs("immigration", ALLOWED) == []
    assert filter_topic_slugs(None, ALLOWED) == []


def test_parse_vote_classification():
    slugs, confidence = parse_vote_classification(
        {"topic_slugs": ["immigration", "xxx"], "confidence": 0.87},
        ALLOWED,
    )
    assert slugs == ["immigration"]
    assert confidence == 0.87


def test_clamp_confidence():
    assert clamp_confidence(1.5) == 1.0
    assert clamp_confidence(-0.2) == 0.0
    assert clamp_confidence("nope") is None
    assert clamp_confidence(None) is None


def test_parse_program_claims_validates_fields():
    data = {
        "claims": [
            {
                "topic_slug": "immigration",
                "stance": "pour",
                "summary": "Durcir les conditions d'asile",
                "quote": "Nous voulons…",
                "confidence": 0.9,
            },
            {
                "topic_slug": "fiscalite",
                "stance": "maybe",
                "summary": "Invalid stance",
            },
            {
                "topic_slug": "nope",
                "stance": "contre",
                "summary": "Unknown topic",
            },
            {
                "topic_slug": "securite",
                "stance": "contre",
                "summary": "ab",
            },
            {
                "topic_slug": "energie-climat",
                "stance": "nuance",
                "summary": "Maintenir le nucléaire et accélérer les renouvelables",
                "quote": None,
                "confidence": "0.4",
            },
        ]
    }
    parsed = parse_program_claims(data, ALLOWED)
    assert len(parsed) == 2
    assert parsed[0]["topic_slug"] == "immigration"
    assert parsed[0]["stance"] == "pour"
    assert parsed[1]["topic_slug"] == "energie-climat"
    assert parsed[1]["confidence"] == 0.4
