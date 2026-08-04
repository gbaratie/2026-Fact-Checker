"""Include chamber in parliamentary vote uniqueness

Revision ID: 004
Revises: 003
Create Date: 2026-08-04
"""

from typing import Sequence, Union

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_votes_candidate_scrutin", "parliamentary_votes", type_="unique")
    op.create_unique_constraint(
        "uq_votes_candidate_chamber_scrutin",
        "parliamentary_votes",
        ["candidate_id", "chamber", "scrutin_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_votes_candidate_chamber_scrutin", "parliamentary_votes", type_="unique"
    )
    op.create_unique_constraint(
        "uq_votes_candidate_scrutin",
        "parliamentary_votes",
        ["candidate_id", "scrutin_id"],
    )
