"""Add topics, claims, and vote_topics tables

Revision ID: 005
Revises: 004
Create Date: 2026-08-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_topics_slug"),
    )
    op.create_index(op.f("ix_topics_slug"), "topics", ["slug"], unique=False)

    op.create_table(
        "claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stance", sa.String(length=20), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("evidence_type", sa.String(length=50), nullable=False),
        sa.Column("interview_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("program_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("article_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("method", sa.String(length=50), nullable=False, server_default="manual"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"]),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"]),
        sa.ForeignKeyConstraint(["program_document_id"], ["program_documents.id"]),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_claims_candidate_id"), "claims", ["candidate_id"], unique=False)
    op.create_index(op.f("ix_claims_topic_id"), "claims", ["topic_id"], unique=False)

    op.create_table(
        "vote_topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"]),
        sa.ForeignKeyConstraint(["vote_id"], ["parliamentary_votes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vote_id", "topic_id", name="uq_vote_topics_vote_topic"),
    )
    op.create_index(op.f("ix_vote_topics_vote_id"), "vote_topics", ["vote_id"], unique=False)
    op.create_index(op.f("ix_vote_topics_topic_id"), "vote_topics", ["topic_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_vote_topics_topic_id"), table_name="vote_topics")
    op.drop_index(op.f("ix_vote_topics_vote_id"), table_name="vote_topics")
    op.drop_table("vote_topics")
    op.drop_index(op.f("ix_claims_topic_id"), table_name="claims")
    op.drop_index(op.f("ix_claims_candidate_id"), table_name="claims")
    op.drop_table("claims")
    op.drop_index(op.f("ix_topics_slug"), table_name="topics")
    op.drop_table("topics")
