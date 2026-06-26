"""
Tests for BankingRepository — PostgreSQL storage layer.

Requires a running PostgreSQL instance. By default uses:
    postgresql://docintel:docintel_dev@localhost:5433/docintel

Override with DATABASE_URL environment variable.

Run:
    cd backend && python -m pytest tests/banking/test_banking_repository.py -v
"""

import os
import uuid

import pytest
import pytest_asyncio

# Skip entire module if asyncpg is not installed or DB is unreachable
asyncpg = pytest.importorskip("asyncpg")

from storage.banking_repository import BankingRepository  # noqa: E402

pytestmark = pytest.mark.asyncio

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://docintel:docintel_dev@localhost:5433/docintel",
)


@pytest_asyncio.fixture
async def repo():
    """Create a BankingRepository per test, init schema, yield, then clean up."""
    r = BankingRepository(DATABASE_URL)
    await r.connect()
    await r.init_schema()
    yield r
    # Clean up test data
    try:
        async with r._pool.acquire() as conn:
            await conn.execute("DELETE FROM transactions")
            await conn.execute("DELETE FROM statements")
    except Exception:
        pass
    await r.close()


# --------------------------------------------------------------------------
# Sample data helpers
# --------------------------------------------------------------------------

def _sample_header(**overrides):
    base = {
        "bank_name": "Vietcombank",
        "account_number": "0011004567890",
        "account_holder": "NGUYEN VAN A",
        "currency": "VND",
        "statement_period_start": "2025-04-01",
        "statement_period_end": "2025-04-30",
        "opening_balance": 45000000,
        "closing_balance": 52300000,
        "total_credit": 35000000,
        "total_debit": 27700000,
    }
    base.update(overrides)
    return base


def _sample_transactions(n=3):
    return [
        {
            "transaction_date": "2025-04-01",
            "description": "LUONG T04/2025 - CONG TY ABC",
            "debit_amount": None,
            "credit_amount": 35000000,
            "balance": 80000000,
            "category": "salary",
            "subcategory": "monthly_salary",
            "category_confidence": 0.95,
            "category_method": "rule_based",
        },
        {
            "transaction_date": "2025-04-02",
            "description": "CK CHO NGUYEN THI B - TIEN THUE NHA",
            "debit_amount": 8000000,
            "credit_amount": None,
            "balance": 72000000,
            "category": "rent_mortgage",
            "subcategory": "",
            "category_confidence": 0.90,
            "category_method": "rule_based",
        },
        {
            "transaction_date": "2025-04-03",
            "description": "THANH TOAN THE - GRAB",
            "debit_amount": 85000,
            "credit_amount": None,
            "balance": 71915000,
            "category": "transportation",
            "subcategory": "ride_hailing",
            "category_confidence": 0.95,
            "category_method": "rule_based",
        },
    ][:n]


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

async def test_init_schema(repo):
    """Schema creation should be idempotent."""
    # Calling init_schema again should not raise
    await repo.init_schema()


async def test_store_and_get_statement(repo):
    """Store a statement and retrieve it by ID."""
    header = _sample_header()
    stmt_id = await repo.store_statement(
        filename="vcb_statement.pdf",
        header=header,
        analytics={"cash_flow": {"total_income": 35000000}},
        processing_tier="Advance",
    )

    assert stmt_id is not None
    assert len(stmt_id) == 36  # UUID format

    # Retrieve
    stmt = await repo.get_statement(stmt_id)
    assert stmt is not None
    assert stmt["filename"] == "vcb_statement.pdf"
    assert stmt["bank_name"] == "Vietcombank"
    assert stmt["account_number"] == "0011004567890"
    assert stmt["currency"] == "VND"
    assert stmt["opening_balance"] == 45000000
    assert stmt["closing_balance"] == 52300000
    assert stmt["processing_tier"] == "Advance"
    assert stmt["analytics_json"] is not None


async def test_get_statement_not_found(repo):
    """Getting a non-existent statement should return None."""
    result = await repo.get_statement(str(uuid.uuid4()))
    assert result is None


async def test_store_and_get_transactions(repo):
    """Store transactions and retrieve them."""
    header = _sample_header(bank_name="BIDV")
    stmt_id = await repo.store_statement(
        filename="bidv_test.pdf", header=header,
    )

    txns = _sample_transactions(3)
    count = await repo.store_transactions(stmt_id, txns)
    assert count == 3

    # Retrieve
    result = await repo.get_transactions(stmt_id)
    assert len(result) == 3

    # Check first transaction
    first = result[0]
    assert first["description"] == "LUONG T04/2025 - CONG TY ABC"
    assert first["category"] == "salary"
    assert first["credit_amount"] == 35000000

    # Verify transaction_count was updated on statement
    stmt = await repo.get_statement(stmt_id)
    assert stmt["transaction_count"] == 3


async def test_get_transactions_with_category_filter(repo):
    """Filter transactions by category."""
    header = _sample_header(bank_name="TCB")
    stmt_id = await repo.store_statement(
        filename="tcb_filter.pdf", header=header,
    )
    await repo.store_transactions(stmt_id, _sample_transactions(3))

    # Filter by salary
    salary_txns = await repo.get_transactions(stmt_id, category="salary")
    assert len(salary_txns) == 1
    assert salary_txns[0]["category"] == "salary"

    # Filter by transportation
    transport = await repo.get_transactions(stmt_id, category="transportation")
    assert len(transport) == 1


async def test_delete_statement_cascades(repo):
    """Deleting a statement should cascade-delete its transactions."""
    header = _sample_header(bank_name="MBBank")
    stmt_id = await repo.store_statement(
        filename="mb_delete.pdf", header=header,
    )
    await repo.store_transactions(stmt_id, _sample_transactions(2))

    # Verify data exists
    assert await repo.get_statement(stmt_id) is not None
    assert len(await repo.get_transactions(stmt_id)) == 2

    # Delete
    deleted = await repo.delete_statement(stmt_id)
    assert deleted is True

    # Verify cascade
    assert await repo.get_statement(stmt_id) is None
    assert len(await repo.get_transactions(stmt_id)) == 0


async def test_delete_statement_not_found(repo):
    """Deleting a non-existent statement should return False."""
    deleted = await repo.delete_statement(str(uuid.uuid4()))
    assert deleted is False


async def test_list_statements_with_bank_filter(repo):
    """List statements filtered by bank name."""
    # Store statements for different banks
    for bank in ["ACB_test_list", "VPBank_test_list"]:
        header = _sample_header(bank_name=bank)
        await repo.store_statement(filename=f"{bank}.pdf", header=header)

    # Filter by ACB
    results = await repo.list_statements(bank_name="ACB_test_list")
    assert len(results) >= 1
    assert all("ACB_test_list" in r["bank_name"] for r in results)


async def test_list_statements_pagination(repo):
    """Pagination with limit and offset."""
    # Insert at least 2 statements
    for i in range(3):
        header = _sample_header(bank_name=f"PaginationBank_{i}")
        await repo.store_statement(filename=f"page_{i}.pdf", header=header)

    # Get all statements
    all_stmts = await repo.list_statements(limit=200)
    assert len(all_stmts) >= 2

    # Get first page
    page1 = await repo.list_statements(limit=1, offset=0)
    assert len(page1) == 1

    # Get second page
    page2 = await repo.list_statements(limit=1, offset=1)
    assert len(page2) == 1

    # They should be different statements
    assert page1[0]["id"] != page2[0]["id"]


async def test_get_stats(repo):
    """Stats should return aggregate counts."""
    # Insert data first
    header = _sample_header(bank_name="StatsTestBank")
    stmt_id = await repo.store_statement(
        filename="stats_test.pdf", header=header,
    )
    await repo.store_transactions(stmt_id, _sample_transactions(2))

    stats = await repo.get_stats()

    assert "total_statements" in stats
    assert "total_transactions" in stats
    assert "banks" in stats
    assert isinstance(stats["banks"], list)
    assert stats["total_statements"] > 0
    assert stats["total_transactions"] > 0
