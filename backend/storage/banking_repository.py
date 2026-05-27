"""
Banking Repository — Async PostgreSQL storage for banking data mining results.

Uses asyncpg for high-performance async PostgreSQL access.
Schema is auto-created on first connect via init_schema().

Tables:
    statements   — extracted bank statement headers (1 per processed file)
    transactions — categorized transactions belonging to a statement

Usage:
    from storage.banking_repository import BankingRepository

    repo = BankingRepository(database_url)
    await repo.connect()
    await repo.init_schema()

    statement_id = await repo.store_statement({...})
    await repo.store_transactions(statement_id, [...])

    await repo.close()
"""

import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import asyncpg

logger = logging.getLogger(__name__)


# =============================================================================
# SQL DDL
# =============================================================================

_CREATE_STATEMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS statements (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename        TEXT NOT NULL,
    bank_name       TEXT,
    account_number  TEXT,
    account_holder  TEXT,
    currency        TEXT DEFAULT 'VND',
    period_start    DATE,
    period_end      DATE,
    opening_balance NUMERIC(18,2),
    closing_balance NUMERIC(18,2),
    total_credit    NUMERIC(18,2),
    total_debit     NUMERIC(18,2),
    transaction_count INTEGER DEFAULT 0,
    processing_tier TEXT DEFAULT 'Advance',
    analytics_json  JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_CREATE_TRANSACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS transactions (
    id              SERIAL PRIMARY KEY,
    statement_id    UUID NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
    transaction_date DATE,
    description     TEXT,
    debit_amount    NUMERIC(18,2),
    credit_amount   NUMERIC(18,2),
    balance         NUMERIC(18,2),
    category        TEXT DEFAULT 'other',
    subcategory     TEXT DEFAULT '',
    category_confidence REAL DEFAULT 0.0,
    category_method TEXT DEFAULT 'default',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_txn_statement ON transactions(statement_id);",
    "CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(transaction_date);",
    "CREATE INDEX IF NOT EXISTS idx_txn_category ON transactions(category);",
    "CREATE INDEX IF NOT EXISTS idx_stmt_bank ON statements(bank_name);",
    "CREATE INDEX IF NOT EXISTS idx_stmt_period ON statements(period_start, period_end);",
]


# =============================================================================
# Repository
# =============================================================================

class BankingRepository:
    """Async PostgreSQL repository for banking data mining results."""

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
        logger.info("Connecting to PostgreSQL: %s", _mask_url(self._database_url))

        # Append sslmode=disable if not already specified, since local Docker
        # PostgreSQL does not support SSL by default.
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
        logger.info("PostgreSQL connection pool created")

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL connection pool closed")

    async def init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_STATEMENTS_TABLE)
            await conn.execute(_CREATE_TRANSACTIONS_TABLE)
            for idx_sql in _CREATE_INDEXES:
                await conn.execute(idx_sql)
        logger.info("Banking database schema initialized")

    # ------------------------------------------------------------------
    # Statements CRUD
    # ------------------------------------------------------------------

    async def store_statement(
        self,
        filename: str,
        header: Dict[str, Any],
        analytics: Optional[Dict[str, Any]] = None,
        processing_tier: str = "Advance",
    ) -> str:
        """
        Store a processed bank statement header.

        Args:
            filename: Original uploaded filename.
            header: Extracted header dict from the extraction step.
            analytics: Analytics snapshot dict (stored as JSONB).
            processing_tier: Tier used for processing.

        Returns:
            The UUID of the newly created statement.
        """
        stmt_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO statements (
                    id, filename, bank_name, account_number, account_holder,
                    currency, period_start, period_end,
                    opening_balance, closing_balance, total_credit, total_debit,
                    transaction_count, processing_tier, analytics_json,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8,
                    $9, $10, $11, $12,
                    $13, $14, $15::jsonb,
                    $16, $17
                )
                """,
                stmt_id,
                filename,
                header.get("bank_name"),
                header.get("account_number"),
                header.get("account_holder"),
                header.get("currency", "VND"),
                _parse_date(header.get("statement_period_start")),
                _parse_date(header.get("statement_period_end")),
                _to_decimal(header.get("opening_balance")),
                _to_decimal(header.get("closing_balance")),
                _to_decimal(header.get("total_credit")),
                _to_decimal(header.get("total_debit")),
                0,  # transaction_count — updated after storing transactions
                processing_tier,
                _json_dumps(analytics),
                now,
                now,
            )

        logger.info("Stored statement %s for file '%s'", stmt_id, filename)
        return stmt_id

    async def get_statement(self, statement_id: str) -> Optional[Dict[str, Any]]:
        """Get a single statement by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM statements WHERE id = $1", statement_id,
            )
        return _row_to_dict(row) if row else None

    async def list_statements(
        self,
        bank_name: Optional[str] = None,
        account_number: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List statements with optional filters and pagination.

        Args:
            bank_name: Filter by bank name (case-insensitive partial match).
            account_number: Filter by account number (partial match).
            date_from: Filter statements with period_start >= date_from.
            date_to: Filter statements with period_end <= date_to.
            limit: Max results (default 50).
            offset: Pagination offset.

        Returns:
            List of statement dicts ordered by created_at DESC.
        """
        conditions = []
        params: list = []
        idx = 1

        if bank_name:
            conditions.append(f"LOWER(bank_name) LIKE LOWER(${idx})")
            params.append(f"%{bank_name}%")
            idx += 1

        if account_number:
            conditions.append(f"account_number LIKE ${idx}")
            params.append(f"%{account_number}%")
            idx += 1

        if date_from:
            conditions.append(f"period_start >= ${idx}")
            params.append(_parse_date(date_from))
            idx += 1

        if date_to:
            conditions.append(f"period_end <= ${idx}")
            params.append(_parse_date(date_to))
            idx += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = f"""
            SELECT * FROM statements
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        params.extend([limit, offset])

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [_row_to_dict(r) for r in rows]

    async def delete_statement(self, statement_id: str) -> bool:
        """
        Delete a statement and all its transactions (CASCADE).

        Returns:
            True if a statement was deleted, False if not found.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM statements WHERE id = $1", statement_id,
            )
        deleted = result == "DELETE 1"
        if deleted:
            logger.info("Deleted statement %s", statement_id)
        return deleted

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    async def store_transactions(
        self, statement_id: str, transactions: list,
    ) -> int:
        """
        Bulk-insert categorized transactions for a statement.

        Args:
            statement_id: Parent statement UUID.
            transactions: List of transaction dicts (from CategorizedTransaction).

        Returns:
            Number of transactions inserted.
        """
        if not transactions:
            return 0

        now = datetime.now(timezone.utc)
        rows = [
            (
                statement_id,
                _parse_date(t.get("transaction_date")),
                t.get("description", ""),
                _to_decimal(t.get("debit_amount")),
                _to_decimal(t.get("credit_amount")),
                _to_decimal(t.get("balance")),
                t.get("category", "other"),
                t.get("subcategory", ""),
                t.get("category_confidence", 0.0),
                t.get("category_method", "default"),
                now,
            )
            for t in transactions
        ]

        async with self._pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO transactions (
                    statement_id, transaction_date, description,
                    debit_amount, credit_amount, balance,
                    category, subcategory, category_confidence, category_method,
                    created_at
                ) VALUES (
                    $1, $2, $3,
                    $4, $5, $6,
                    $7, $8, $9, $10,
                    $11
                )
                """,
                rows,
            )

            # Update transaction_count on the parent statement
            await conn.execute(
                """
                UPDATE statements
                SET transaction_count = $1, updated_at = $2
                WHERE id = $3
                """,
                len(transactions),
                now,
                statement_id,
            )

        logger.info(
            "Stored %d transactions for statement %s",
            len(transactions), statement_id,
        )
        return len(transactions)

    async def get_transactions(
        self,
        statement_id: str,
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get transactions for a statement with optional filters."""
        conditions = ["statement_id = $1"]
        params: list = [statement_id]
        idx = 2

        if category:
            conditions.append(f"category = ${idx}")
            params.append(category)
            idx += 1

        if date_from:
            conditions.append(f"transaction_date >= ${idx}")
            params.append(_parse_date(date_from))
            idx += 1

        if date_to:
            conditions.append(f"transaction_date <= ${idx}")
            params.append(_parse_date(date_to))
            idx += 1

        where_clause = " AND ".join(conditions)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT * FROM transactions
                WHERE {where_clause}
                ORDER BY transaction_date ASC, id ASC
                """,
                *params,
            )

        return [_row_to_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_stats(self) -> Dict[str, Any]:
        """Get high-level stats about stored banking data."""
        async with self._pool.acquire() as conn:
            stmt_count = await conn.fetchval(
                "SELECT COUNT(*) FROM statements"
            )
            txn_count = await conn.fetchval(
                "SELECT COUNT(*) FROM transactions"
            )
            banks = await conn.fetch(
                """
                SELECT bank_name, COUNT(*) as count
                FROM statements
                WHERE bank_name IS NOT NULL
                GROUP BY bank_name
                ORDER BY count DESC
                """
            )
            latest = await conn.fetchval(
                "SELECT MAX(created_at) FROM statements"
            )

        return {
            "total_statements": stmt_count or 0,
            "total_transactions": txn_count or 0,
            "banks": [
                {"bank_name": r["bank_name"], "statement_count": r["count"]}
                for r in banks
            ],
            "latest_processed_at": latest.isoformat() if latest else None,
        }


# =============================================================================
# Module-level helpers
# =============================================================================

def _parse_date(value: Any) -> Optional[date]:
    """Convert a date string (YYYY-MM-DD) or date object to datetime.date.

    asyncpg requires native date objects, not strings.
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _to_decimal(value: Any) -> Optional[Decimal]:
    """Safely convert a value to Decimal for NUMERIC columns."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _json_dumps(data: Any) -> Optional[str]:
    """Serialize dict to JSON string for JSONB column."""
    if data is None:
        return None
    import json
    return json.dumps(data, default=str)


def _row_to_dict(row: asyncpg.Record) -> Dict[str, Any]:
    """Convert an asyncpg Record to a plain dict with JSON-safe values."""
    result = dict(row)
    for key, val in result.items():
        if isinstance(val, Decimal):
            result[key] = float(val)
        elif isinstance(val, datetime):
            result[key] = val.isoformat()
        elif isinstance(val, uuid.UUID):
            result[key] = str(val)
        elif hasattr(val, 'isoformat'):
            result[key] = val.isoformat()
    return result


def _mask_url(url: str) -> str:
    """Mask password in database URL for safe logging."""
    try:
        # postgresql://user:password@host:port/db → postgresql://user:***@host:port/db
        if "://" in url and "@" in url:
            scheme_rest = url.split("://", 1)
            user_pass_host = scheme_rest[1].split("@", 1)
            user_pass = user_pass_host[0]
            if ":" in user_pass:
                user = user_pass.split(":", 1)[0]
                return f"{scheme_rest[0]}://{user}:***@{user_pass_host[1]}"
        return url
    except Exception:
        return "***"
