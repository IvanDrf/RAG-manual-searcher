"""Add source text and the persisted BM25 index."""

# Alembic uses revision-specific names and a dynamic operations proxy.
# pylint: disable=invalid-name,no-member

import sqlalchemy as sa
from pgvector.sqlalchemy import SPARSEVEC

from alembic import op

revision = "6c3874f501ab"
down_revision = "3acd89051d58"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Allow lexical imports and create the index tables."""
    op.add_column("chunks", sa.Column("source_text", sa.Text()))
    op.alter_column("chunks", "embedding", nullable=True)
    op.create_table(
        "bm25_terms",
        sa.Column("term", sa.Text(), primary_key=True),
        sa.Column("block", sa.Integer(), nullable=False),
        sa.Column("coordinate", sa.Integer(), nullable=False),
    )
    op.create_table(
        "bm25_blocks",
        sa.Column("block", sa.Integer(), primary_key=True),
        sa.Column(
            "chunk_id",
            sa.Uuid(),
            sa.ForeignKey("chunks.chunk_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("weights", SPARSEVEC(1000), nullable=False),
    )
    op.create_index("ix_bm25_blocks_chunk_id", "bm25_blocks", ["chunk_id"])


def downgrade() -> None:
    """Restore the old schema once every chunk has a dense embedding."""
    op.alter_column("chunks", "embedding", nullable=False)
    op.drop_table("bm25_blocks")
    op.drop_table("bm25_terms")
    op.drop_column("chunks", "source_text")
