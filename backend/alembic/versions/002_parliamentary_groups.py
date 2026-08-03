"""Add parliamentary groups and vote group position

Revision ID: 002
Revises: 001
Create Date: 2026-08-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parliamentary_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clair_id", sa.String(length=64), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column("chamber", sa.String(length=20), nullable=False),
        sa.Column("legislature", sa.Integer(), nullable=True),
        sa.Column("spectrum", sa.String(length=50), nullable=True),
        sa.Column("raw_metadata", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clair_id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        op.f("ix_parliamentary_groups_slug"), "parliamentary_groups", ["slug"], unique=True
    )

    op.add_column(
        "candidates",
        sa.Column("parliamentary_group_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_candidates_parliamentary_group_id",
        "candidates",
        "parliamentary_groups",
        ["parliamentary_group_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_candidates_parliamentary_group_id"),
        "candidates",
        ["parliamentary_group_id"],
        unique=False,
    )

    op.add_column(
        "parliamentary_votes",
        sa.Column("group_position", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "parliamentary_votes",
        sa.Column("parliamentary_group_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_votes_parliamentary_group_id",
        "parliamentary_votes",
        "parliamentary_groups",
        ["parliamentary_group_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_votes_parliamentary_group_id", "parliamentary_votes", type_="foreignkey")
    op.drop_column("parliamentary_votes", "parliamentary_group_id")
    op.drop_column("parliamentary_votes", "group_position")
    op.drop_index(op.f("ix_candidates_parliamentary_group_id"), table_name="candidates")
    op.drop_constraint("fk_candidates_parliamentary_group_id", "candidates", type_="foreignkey")
    op.drop_column("candidates", "parliamentary_group_id")
    op.drop_index(op.f("ix_parliamentary_groups_slug"), table_name="parliamentary_groups")
    op.drop_table("parliamentary_groups")
