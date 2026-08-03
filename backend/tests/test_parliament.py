from app.connectors.parliament import ParliamentConnector
from app.utils.text import normalize_text


def test_normalize_matches_clair_names():
    assert normalize_text("François Ruffin") == "francois ruffin"
    assert normalize_text("Jean-Luc Mélenchon") == "jean luc melenchon"


def test_best_name_match_rejects_fuzzy_false_positives():
    connector = ParliamentConnector()
    items = [
        {"id": "1", "slug": "emmanuel-mandon", "prenom": "Emmanuel", "nom": "Mandon", "actif": True},
        {"id": "2", "slug": "emmanuel-maurel", "prenom": "Emmanuel", "nom": "Maurel", "actif": True},
    ]
    assert connector._best_name_match("Emmanuel Macron", items) is None


def test_best_name_match_accepts_exact():
    connector = ParliamentConnector()
    items = [
        {
            "id": "86d",
            "slug": "francois-ruffin",
            "prenom": "François",
            "nom": "Ruffin",
            "actif": True,
        },
        {
            "id": "other",
            "slug": "autre-ruffin",
            "prenom": "Autre",
            "nom": "Ruffin",
            "actif": True,
        },
    ]
    match = connector._best_name_match("François Ruffin", items)
    assert match is not None
    assert match.slug == "francois-ruffin"


def test_parse_clair_votes_uses_scrutin_numero():
    connector = ParliamentConnector()
    payload = {
        "data": [
            {
                "position": "contre",
                "scrutin": {
                    "id": "uuid-1",
                    "numero": 8434,
                    "chambre": "assemblee",
                    "date": "2026-07-21T00:00:00.000Z",
                    "titre": "Proposition de loi test",
                },
            }
        ]
    }
    records = connector._parse_clair_votes(payload)
    assert len(records) == 1
    assert records[0].scrutin_id == "8434"
    assert records[0].position == "contre"
    assert records[0].chamber == "assemblee"
