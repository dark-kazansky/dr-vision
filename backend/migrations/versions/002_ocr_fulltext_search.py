"""OCR full-text search — tsvector generated column + GIN index.

Revision ID: 002
Revises: 001
Create Date: 2026-06-26

feat-070: Full-text Document Search. Adds a generated tsvector column on
``ocr_results.raw_text`` (using the 'simple' text-search config so Vietnamese
diacritics and other non-English content match correctly) plus a GIN index
over it. Additive and idempotent — safe to re-run.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Generated tsvector column maintained automatically from raw_text.
    # 'simple' config: language-agnostic, preserves diacritics, no stemming.
    op.execute(
        """
        ALTER TABLE ocr_results
        ADD COLUMN IF NOT EXISTS search_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('simple', coalesce(raw_text, ''))) STORED
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ocr_search_tsv "
        "ON ocr_results USING gin(search_tsv)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_ocr_search_tsv")
    op.execute("ALTER TABLE ocr_results DROP COLUMN IF EXISTS search_tsv")
