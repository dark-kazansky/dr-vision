"""
OCR Result Repository — Async PostgreSQL storage for OCR processing results.

Stores raw OCR text, parsed output, classification, extraction, and split
results as JSONB in a single table.

Usage:
    from storage.ocr_result_repository import OcrResultRepository

    repo = OcrResultRepository(database_url)
    await repo.connect()
    await repo.init_schema()

    result_id = await repo.store_result(filename="invoice.pdf", ...)
    await repo.get_result(result_id)
    await repo.list_results(limit=20)

    await repo.close()
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import asyncpg

logger = logging.getLogger(__name__)


# =============================================================================
# SQL DDL
# =============================================================================

_CREATE_OCR_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS ocr_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename        TEXT NOT NULL,
    model_id        TEXT,
    provider        TEXT,
    tier            TEXT DEFAULT 'Normal',
    raw_text        TEXT,
    result_data     JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

# Additive ALTER: add a generated tsvector column for full-text search.
# Uses the 'simple' text-search config (language-agnostic, preserves diacritics,
# no stemming) so Vietnamese and other non-English content matches correctly.
# GENERATED ALWAYS AS ... STORED auto-maintains the column from raw_text.
_ADD_SEARCH_TSV_COLUMN = """
ALTER TABLE ocr_results
ADD COLUMN IF NOT EXISTS search_tsv tsvector
GENERATED ALWAYS AS (to_tsvector('simple', coalesce(raw_text, ''))) STORED;
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_ocr_filename ON ocr_results(filename);",
    "CREATE INDEX IF NOT EXISTS idx_ocr_model ON ocr_results(model_id);",
    "CREATE INDEX IF NOT EXISTS idx_ocr_created ON ocr_results(created_at DESC);",
    (
        "CREATE INDEX IF NOT EXISTS idx_ocr_result_type "
        "ON ocr_results USING gin ((result_data -> 'type'));"
    ),
    # GIN index over the generated tsvector column powers full-text search.
    "CREATE INDEX IF NOT EXISTS idx_ocr_search_tsv ON ocr_results USING gin(search_tsv);",
]


# =============================================================================
# Repository
# =============================================================================


class OcrResultRepository:
    """Async PostgreSQL repository for OCR processing results."""

    def __init__(self, database_url: str):
        self._database_url = database_url
        self._pool: Optional[asyncpg.Pool] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Create a connection pool to the database."""
        if self._pool is not None:
            return

        dsn = self._database_url
        if "sslmode" not in dsn:
            separator = "&" if "?" in dsn else "?"
            dsn = f"{dsn}{separator}sslmode=disable"

        self._pool = await asyncpg.create_pool(
            dsn,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("OcrResultRepository: connection pool created")

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("OcrResultRepository: connection pool closed")

    async def init_schema(self) -> None:
        """Create table and indexes if they don't exist."""
        if not self._pool:
            raise RuntimeError("Not connected")
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_OCR_RESULTS_TABLE)
            # Additive migration: add tsvector column before the GIN index.
            await conn.execute(_ADD_SEARCH_TSV_COLUMN)
            for idx_sql in _CREATE_INDEXES:
                await conn.execute(idx_sql)
        logger.info("OCR results schema initialized")

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    async def store_result(
        self,
        filename: str,
        raw_text: str,
        *,
        model_id: Optional[str] = None,
        provider: Optional[str] = None,
        tier: str = "Normal",
        result_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store an OCR processing result.

        Args:
            filename: Original uploaded filename.
            raw_text: Raw OCR text output.
            model_id: AI model used for processing.
            provider: Model provider (lmstudio, gemini, bedrock, etc.).
            tier: Processing tier (Normal, Advance, etc.).
            result_data: JSONB payload — may contain:
                - type: "parse" | "classify" | "extract" | "split"
                - parsed_text: formatted text after parsing
                - file_type: source file type (pdf, png, jpg)
                - is_scanned: whether OCR was required
                - pages: number of pages
                - classification: classification result
                - extraction: extracted structured data
                - split_result: split segments

        Returns:
            UUID of the stored result (as string).
        """
        if not self._pool:
            raise RuntimeError("Not connected")

        result_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        data_json = json.dumps(result_data or {}, ensure_ascii=False)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ocr_results (id, filename, model_id, provider, tier, raw_text, result_data, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
                """,
                result_id,
                filename,
                model_id,
                provider,
                tier,
                raw_text,
                data_json,
                now,
            )

        logger.info("Stored OCR result %s for file: %s", result_id, filename)
        return str(result_id)

    async def update_result_data(
        self,
        result_id: str,
        patch: Dict[str, Any],
    ) -> None:
        """
        Merge additional data into the result_data JSONB field.

        Uses jsonb_concat (||) to merge without overwriting existing keys
        unless the patch contains the same key.
        """
        if not self._pool:
            raise RuntimeError("Not connected")

        patch_json = json.dumps(patch, ensure_ascii=False)
        uid = uuid.UUID(result_id)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE ocr_results
                SET result_data = result_data || $1::jsonb
                WHERE id = $2
                """,
                patch_json,
                uid,
            )

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    async def get_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """Get a single OCR result by ID."""
        if not self._pool:
            raise RuntimeError("Not connected")

        uid = uuid.UUID(result_id)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ocr_results WHERE id = $1", uid
            )

        return _row_to_dict(row) if row else None

    async def get_result_by_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get the most recent OCR result for a given filename."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM ocr_results
                WHERE filename = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                filename,
            )

        return _row_to_dict(row) if row else None

    async def list_results(
        self,
        limit: int = 50,
        offset: int = 0,
        filename_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List OCR results with pagination and optional filename search."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            if filename_filter:
                pattern = f"%{filename_filter}%"
                rows = await conn.fetch(
                    """
                    SELECT * FROM ocr_results
                    WHERE filename ILIKE $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    pattern,
                    limit,
                    offset,
                )
                total = await conn.fetchval(
                    "SELECT COUNT(*) FROM ocr_results WHERE filename ILIKE $1",
                    pattern,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM ocr_results
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit,
                    offset,
                )
                total = await conn.fetchval("SELECT COUNT(*) FROM ocr_results")

        return {
            "items": [_row_to_dict(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def search_text(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full-text search across OCR result ``raw_text`` using PostgreSQL tsvector.

        Uses ``websearch_to_tsquery`` which accepts user input safely (supports
        quoted phrases, ``OR``, ``-`` negation) and never raises on syntax.
        Results are ranked with ``ts_rank`` and a snippet is produced with
        ``ts_headline``. Highlight delimiters use control characters
        (``\\x01`` / ``\\x02``) so the frontend can escape HTML first, then
        convert the delimiters to ``<mark>`` tags (XSS-safe highlighting).

        Args:
            query: Free-text search query.
            limit: Maximum number of hits to return (1..200).
            offset: Pagination offset.
            date_from: Optional ISO 8601 timestamp; only results created at or
                after this moment are returned.
            date_to: Optional ISO 8601 timestamp; only results created at or
                before this moment are returned.

        Returns:
            ``{"items", "total", "limit", "offset", "query"}`` where each item
            has the standard OCR result fields plus ``rank`` (float) and
            ``snippet`` (str with ``\\x01``/``\\x02`` highlight markers).
        """
        if not self._pool:
            raise RuntimeError("Not connected")

        empty_result: Dict[str, Any] = {
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "query": query,
        }

        stripped = (query or "").strip()
        if not stripped:
            return empty_result

        # Build optional date filters with positional parameters.
        # Parameter layout: $1 = tsquery string, then date_from, date_to,
        # then limit, offset. We assemble the WHERE clause dynamically.
        conditions = ["search_tsv @@ q"]
        params: list = [stripped]
        next_idx = 2
        if date_from:
            conditions.append(f"created_at >= ${next_idx}")
            params.append(date_from)
            next_idx += 1
        if date_to:
            conditions.append(f"created_at <= ${next_idx}")
            params.append(date_to)
            next_idx += 1
        where_sql = " AND ".join(conditions)

        # Position of limit/offset params comes after the date params.
        limit_idx = next_idx
        offset_idx = next_idx + 1

        # ts_headline options:
        #   StartSel/StopSel = control chars \x01/\x02 (frontend converts to <mark>)
        #   MaxWords/MinWords/MaxFragments tune snippet length
        headline_opts = (
            "StartSel=E'\\x01', StopSel=E'\\x02', "
            "MaxWords=35, MinWords=15, MaxFragments=3, "
            "FragmentDelimiter=' … '"
        )

        select_sql = f"""
            SELECT
                id,
                filename,
                model_id,
                provider,
                tier,
                created_at,
                ts_rank(search_tsv, q) AS rank,
                ts_headline('simple', raw_text, q, '{headline_opts}') AS snippet
            FROM ocr_results, websearch_to_tsquery('simple', $1) AS q
            WHERE {where_sql}
            ORDER BY rank DESC, created_at DESC
            LIMIT ${limit_idx} OFFSET ${offset_idx}
        """
        count_sql = f"""
            SELECT COUNT(*) FROM ocr_results, websearch_to_tsquery('simple', $1) AS q
            WHERE {where_sql}
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(select_sql, *params, limit, offset)
            total = await conn.fetchval(count_sql, *params)

        items = []
        for r in rows:
            items.append({
                "id": str(r["id"]),
                "filename": r["filename"],
                "model_id": r["model_id"],
                "provider": r["provider"],
                "tier": r["tier"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "rank": float(r["rank"]),
                "snippet": r["snippet"],
            })

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "query": query,
        }

    async def delete_result(self, result_id: str) -> bool:
        """Delete an OCR result by ID. Returns True if a row was deleted."""
        if not self._pool:
            raise RuntimeError("Not connected")

        uid = uuid.UUID(result_id)
        async with self._pool.acquire() as conn:
            tag = await conn.execute(
                "DELETE FROM ocr_results WHERE id = $1", uid
            )

        return tag == "DELETE 1"

    async def get_stats(self) -> Dict[str, Any]:
        """Return summary statistics for stored OCR results."""
        if not self._pool:
            raise RuntimeError("Not connected")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) AS total_results,
                    COUNT(DISTINCT filename) AS unique_files,
                    COUNT(DISTINCT model_id) AS models_used,
                    MIN(created_at) AS earliest,
                    MAX(created_at) AS latest
                FROM ocr_results
                """
            )

        return {
            "total_results": row["total_results"],
            "unique_files": row["unique_files"],
            "models_used": row["models_used"],
            "earliest": row["earliest"].isoformat() if row["earliest"] else None,
            "latest": row["latest"].isoformat() if row["latest"] else None,
        }


# =============================================================================
# Helpers
# =============================================================================


def _row_to_dict(row: asyncpg.Record) -> Dict[str, Any]:
    """Convert an asyncpg Record to a plain dict with serializable values."""
    d: Dict[str, Any] = dict(row)

    # UUID → string
    if "id" in d:
        d["id"] = str(d["id"])

    # result_data comes back as a string from jsonb — parse it
    if "result_data" in d and isinstance(d["result_data"], str):
        d["result_data"] = json.loads(d["result_data"])

    # Timestamps → ISO string
    for key in ("created_at",):
        if key in d and d[key] is not None:
            d[key] = d[key].isoformat()

    return d
