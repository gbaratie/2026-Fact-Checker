"""Comparaison claims (déclarations) ↔ votes tagués par thème."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

CoherenceStatus = Literal[
    "aligned",
    "conflict",
    "mixed",
    "abstention_only",
    "claims_only",
    "votes_only",
    "empty",
]

POLAR_STANCES = frozenset({"pour", "contre"})
POLAR_VOTES = frozenset({"pour", "contre"})


def normalize_stance(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().lower() or None


def topic_coherence_status(
    claim_stances: Iterable[str | None],
    vote_positions: Iterable[str | None],
) -> CoherenceStatus:
    claims = {normalize_stance(s) for s in claim_stances}
    claims.discard(None)
    votes = {normalize_stance(p) for p in vote_positions}
    votes.discard(None)

    polar_claims = claims & POLAR_STANCES
    polar_votes = votes & POLAR_VOTES

    if not claims and not votes:
        return "empty"
    if claims and not votes:
        return "claims_only"
    if votes and not claims:
        return "votes_only"
    if not polar_claims and not polar_votes:
        return "abstention_only"

    if polar_claims and polar_votes:
        if polar_claims == polar_votes and len(polar_claims) == 1:
            return "aligned"
        if polar_claims & polar_votes and polar_claims != polar_votes:
            return "mixed"
        if polar_claims.isdisjoint(polar_votes):
            return "conflict"
        return "mixed"

    # Polarité d'un seul côté + abstention/nuance de l'autre
    if polar_claims or polar_votes:
        return "mixed"
    return "abstention_only"
