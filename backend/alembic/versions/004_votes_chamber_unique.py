"""Include chamber in parliamentary vote uniqueness

Revision ID: 004
Revises: 003
Create Date: 2026-08-04
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_CONSTRAINT = "uq_votes_candidate_chamber_scrutin"


def _unique_constraints_on(table: str) -> list[tuple[str, list[str]]]:
    """Retourne [(constraint_name, [colonnes…])] pour les UNIQUE de la table."""
    conn = op.get_bind()
    rows = conn.execute(
        text(
            """
            SELECT c.conname, array_agg(a.attname ORDER BY u.ord)
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS u(attnum, ord) ON true
            JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = u.attnum
            WHERE t.relname = :table
              AND c.contype = 'u'
            GROUP BY c.conname
            """
        ),
        {"table": table},
    ).all()
    return [(name, list(cols)) for name, cols in rows]


def upgrade() -> None:
    # En 001 la contrainte était créée sans nom explicite → Postgres a généré
    # parliamentary_votes_candidate_id_scrutin_id_key (pas uq_votes_candidate_scrutin).
    for name, cols in _unique_constraints_on("parliamentary_votes"):
        if cols == ["candidate_id", "scrutin_id"] or name == "uq_votes_candidate_scrutin":
            op.drop_constraint(name, "parliamentary_votes", type_="unique")

    existing = {name for name, _ in _unique_constraints_on("parliamentary_votes")}
    if NEW_CONSTRAINT not in existing:
        op.create_unique_constraint(
            NEW_CONSTRAINT,
            "parliamentary_votes",
            ["candidate_id", "chamber", "scrutin_id"],
        )


def downgrade() -> None:
    for name, cols in _unique_constraints_on("parliamentary_votes"):
        if cols == ["candidate_id", "chamber", "scrutin_id"] or name == NEW_CONSTRAINT:
            op.drop_constraint(name, "parliamentary_votes", type_="unique")

    existing = {name for name, _ in _unique_constraints_on("parliamentary_votes")}
    if "uq_votes_candidate_scrutin" not in existing:
        op.create_unique_constraint(
            "uq_votes_candidate_scrutin",
            "parliamentary_votes",
            ["candidate_id", "scrutin_id"],
        )
