from pathlib import Path

from app.connectors.programs import ProgramsConnector


def test_programs_seed_loaded_for_all_candidates():
    connector = ProgramsConnector()
    slugs = [
        "marine-le-pen",
        "jordan-bardella",
        "emmanuel-macron",
        "francois-ruffin",
        "jean-luc-melenchon",
        "laurent-wauquiez",
        "fabien-roussel",
        "yannick-jadot",
        "clementine-autain",
        "raphael-glucksmann",
    ]
    for slug in slugs:
        programs = connector.programs_for_slug(slug)
        assert programs, f"expected curated programs for {slug}"
        for prog in programs:
            assert prog["title"]
            assert prog["url"].startswith("http")
            assert prog["kind"] in {
                "presidential_program",
                "party_program",
                "campaign_site",
                "platform_outline",
            }


def test_programs_seed_path_exists():
    assert Path(ProgramsConnector().seeds_path).exists()
