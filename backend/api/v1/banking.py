"""
Banking API — endpoints for banking data mining operations.

Provides:
- POST /api/v1/banking/process       — Full pipeline: parse → classify → extract → categorize → store
- POST /api/v1/banking/categorize    — Categorize pre-extracted transactions
- POST /api/v1/banking/analytics     — Generate analytics from categorized data
- GET  /api/v1/banking/templates     — List available workflow templates
- POST /api/v1/banking/export/csv    — Export categorized transactions as CSV
- GET  /api/v1/banking/statements    — List stored statements (with filters)
- GET  /api/v1/banking/statements/{id} — Get statement detail with transactions
- DELETE /api/v1/banking/statements/{id} — Delete a stored statement
- GET  /api/v1/banking/stats         — Storage overview statistics
"""

import asyncio
import csv
import io
import json
import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from agents.factory import AgentFactory
from components.extractor import Extractor
from components.parser import Parser
from components.transaction_categorizer import TransactionCategorizer
from config import Config, TierConfig
from config.banking_schemas import (
    BANK_STATEMENT_HEADER_SCHEMA,
    BANK_STATEMENT_TRANSACTION_SCHEMA,
    BANKING_CLASSIFICATION_RULES,
    get_schema_for_doc_type,
    list_workflow_templates,
)
from core.middleware import FileSizeValidator
from core.schemas import ExtractionConfig, ExtractionTarget, FieldType, SchemaField
from core.utils import secure_save_file
from services.banking_analytics_service import BankingAnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/banking", tags=["Banking"])

file_size_validator = FileSizeValidator()
analytics_service = BankingAnalyticsService()


def _safe_remove(path: str) -> None:
    import os
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logger.warning("Failed to remove temp file %s: %s", path, e)


def _schema_to_extraction_config(schema: dict) -> ExtractionConfig:
    """Convert a banking schema dict to an ExtractionConfig."""
    return ExtractionConfig(
        target=ExtractionTarget(schema["target"]),
        fields=[
            SchemaField(
                name=f["name"],
                type=FieldType(f["type"]),
                description=f.get("description", ""),
                required=f.get("required", False),
            )
            for f in schema["fields"]
        ],
    )


def _get_repo(request: Request):
    """Get the banking repository from app state, or None if unavailable."""
    return getattr(request.app.state, "banking_repo", None)


# =============================================================================
# GET /api/v1/banking/templates
# =============================================================================

@router.get("/templates")
async def get_templates():
    """List available banking workflow templates."""
    return {
        "success": True,
        "templates": list_workflow_templates(),
    }


# =============================================================================
# POST /api/v1/banking/process
# =============================================================================

@router.post("/process")
async def process_bank_statement(
    request: Request,
    file: UploadFile = File(...),
    tier: str = Form("Advance"),
    use_llm_categorization: bool = Form(True),
):
    """
    Full pipeline: OCR → Extract header → Extract transactions → Categorize → Store.

    Processes a bank statement PDF end-to-end and returns:
    - Extracted header information (bank, account, balances)
    - Categorized transactions with category labels
    - Summary analytics
    - statement_id (if storage is available)
    """
    config = Config.load()

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    max_size_mb = config.upload_config.get("max_size_mb", 10)
    await file_size_validator.validate(file, max_size_mb)

    upload_folder = config.upload_config.get("folder", "uploads")
    try:
        file_path = await secure_save_file(file, upload_folder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    try:
        # Step 1: Parse (OCR)
        parser_model_id, parser_provider = TierConfig.get_parser_model_spec(tier)
        ocr_agent = AgentFactory.create_from_config(
            config, parser_model_id, provider_override=parser_provider
        )
        parser = Parser(ocr_agent=ocr_agent)
        parse_result = await asyncio.to_thread(parser.parse, file_path)

        if not parse_result.success:
            raise HTTPException(status_code=500, detail=f"OCR failed: {parse_result.error}")

        # Step 2: Extract header
        ext_model_id, ext_provider = TierConfig.get_extractor_model_spec(tier)
        llm_agent = AgentFactory.create_llm_agent(
            ext_model_id, config=config, provider=ext_provider
        )
        extractor = Extractor(agent=llm_agent)

        header_config = _schema_to_extraction_config(BANK_STATEMENT_HEADER_SCHEMA)
        header_result = await asyncio.to_thread(
            extractor.extract, parse_result.text, header_config
        )

        header_data = header_result.structured_data if header_result.success else {}

        # Step 3: Extract transactions
        txn_config = _schema_to_extraction_config(BANK_STATEMENT_TRANSACTION_SCHEMA)
        txn_result = await asyncio.to_thread(
            extractor.extract, parse_result.text, txn_config
        )

        transactions = []
        if txn_result.success and txn_result.structured_data:
            raw = txn_result.structured_data
            transactions = raw if isinstance(raw, list) else [raw]

        # Step 4: Categorize
        cat_agent = llm_agent if use_llm_categorization else None
        categorizer = TransactionCategorizer(agent=cat_agent)
        cat_result = categorizer.categorize(
            transactions, use_llm_fallback=use_llm_categorization
        )

        # Step 5: Analytics
        cat_txns = cat_result.transactions if cat_result.success else []
        report = analytics_service.analyze(header_data or {}, cat_txns)

        # Step 6: Store results (if database is available)
        statement_id = None
        repo = _get_repo(request)
        if repo is not None:
            try:
                analytics_snapshot = {
                    "cash_flow": report.cash_flow,
                    "spending_breakdown": report.spending_breakdown,
                    "income_breakdown": report.income_breakdown,
                } if report.success else None

                statement_id = await repo.store_statement(
                    filename=file.filename,
                    header=header_data or {},
                    analytics=analytics_snapshot,
                    processing_tier=tier,
                )

                txn_dicts = [
                    {
                        "transaction_date": t.transaction_date,
                        "description": t.description,
                        "debit_amount": t.debit_amount,
                        "credit_amount": t.credit_amount,
                        "balance": t.balance,
                        "category": t.category,
                        "subcategory": t.subcategory,
                        "category_confidence": t.category_confidence,
                        "category_method": t.category_method,
                    }
                    for t in cat_txns
                ]
                await repo.store_transactions(statement_id, txn_dicts)

                logger.info(
                    "Stored statement %s with %d transactions",
                    statement_id, len(txn_dicts),
                )
            except Exception as e:
                logger.warning("Failed to store results: %s", e)
                # Non-fatal — continue returning the response

        return {
            "success": True,
            "statement_id": statement_id,
            "filename": file.filename,
            "header": header_data,
            "transactions": [
                {
                    "transaction_date": t.transaction_date,
                    "description": t.description,
                    "debit_amount": t.debit_amount,
                    "credit_amount": t.credit_amount,
                    "balance": t.balance,
                    "category": t.category,
                    "subcategory": t.subcategory,
                    "category_confidence": t.category_confidence,
                    "category_method": t.category_method,
                }
                for t in cat_txns
            ],
            "summary": cat_result.summary,
            "analytics": {
                "cash_flow": report.cash_flow,
                "spending_breakdown": report.spending_breakdown,
                "income_breakdown": report.income_breakdown,
                "top_expenses": report.top_expenses,
                "daily_flow": report.daily_flow,
            } if report.success else None,
        }

    finally:
        _safe_remove(file_path)


# =============================================================================
# POST /api/v1/banking/categorize
# =============================================================================

@router.post("/categorize")
async def categorize_transactions(
    transactions: str = Form(...),
    use_llm: bool = Form(True),
    tier: str = Form("Normal"),
):
    """
    Categorize pre-extracted transactions.

    Accepts transactions JSON string and returns categorized results.
    """
    try:
        txn_list = json.loads(transactions)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    if not isinstance(txn_list, list):
        raise HTTPException(status_code=400, detail="transactions must be a JSON array")

    agent = None
    if use_llm:
        config = Config.load()
        model_id, provider = TierConfig.get_extractor_model_spec(tier)
        agent = AgentFactory.create_llm_agent(model_id, config=config, provider=provider)

    categorizer = TransactionCategorizer(agent=agent)
    result = categorizer.categorize(txn_list, use_llm_fallback=use_llm)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return {
        "success": True,
        "transactions": [
            {
                "transaction_date": t.transaction_date,
                "description": t.description,
                "debit_amount": t.debit_amount,
                "credit_amount": t.credit_amount,
                "balance": t.balance,
                "category": t.category,
                "subcategory": t.subcategory,
                "category_confidence": t.category_confidence,
                "category_method": t.category_method,
            }
            for t in result.transactions
        ],
        "summary": result.summary,
    }


# =============================================================================
# POST /api/v1/banking/analytics
# =============================================================================

@router.post("/analytics")
async def generate_analytics(
    header: str = Form(...),
    transactions: str = Form(...),
):
    """
    Generate analytics from pre-categorized data.

    Accepts header and categorized transactions as JSON strings.
    """
    try:
        header_data = json.loads(header)
        txn_list = json.loads(transactions)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    # Convert dicts to CategorizedTransaction objects
    from components.transaction_categorizer import CategorizedTransaction
    cat_txns = [
        CategorizedTransaction(
            transaction_date=t.get("transaction_date"),
            description=t.get("description", ""),
            debit_amount=t.get("debit_amount"),
            credit_amount=t.get("credit_amount"),
            balance=t.get("balance"),
            category=t.get("category", "other"),
            subcategory=t.get("subcategory", ""),
        )
        for t in txn_list
    ]

    report = analytics_service.analyze(header_data, cat_txns)

    if not report.success:
        raise HTTPException(status_code=500, detail=report.error)

    return {
        "success": True,
        "account_info": report.account_info,
        "cash_flow": report.cash_flow,
        "spending_breakdown": report.spending_breakdown,
        "income_breakdown": report.income_breakdown,
        "top_expenses": report.top_expenses,
        "top_income_sources": report.top_income_sources,
        "daily_flow": report.daily_flow,
    }


# =============================================================================
# POST /api/v1/banking/export/csv
# =============================================================================

@router.post("/export/csv")
async def export_csv(
    transactions: str = Form(...),
):
    """
    Export categorized transactions as CSV.

    Returns a downloadable CSV file.
    """
    try:
        txn_list = json.loads(transactions)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "Ngày GD", "Mô tả", "Ghi nợ", "Ghi có", "Số dư",
        "Danh mục", "Danh mục phụ", "Độ tin cậy", "Phương pháp",
    ])

    for t in txn_list:
        writer.writerow([
            t.get("transaction_date", ""),
            t.get("description", ""),
            t.get("debit_amount", ""),
            t.get("credit_amount", ""),
            t.get("balance", ""),
            t.get("category", ""),
            t.get("subcategory", ""),
            t.get("category_confidence", ""),
            t.get("category_method", ""),
        ])

    output.seek(0)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),  # BOM for Excel
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )


# =============================================================================
# GET /api/v1/banking/statements — List stored statements
# =============================================================================

@router.get("/statements")
async def list_statements(
    request: Request,
    bank_name: Optional[str] = Query(None, description="Filter by bank name"),
    account_number: Optional[str] = Query(None, description="Filter by account number"),
    date_from: Optional[str] = Query(None, description="Filter period_start >= date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter period_end <= date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """
    List stored bank statements with optional filters.

    Supports filtering by bank name, account number, and date range.
    Results are ordered by most recently processed first.
    """
    repo = _get_repo(request)
    if repo is None:
        raise HTTPException(
            status_code=503,
            detail="Storage is unavailable — database not connected",
        )

    statements = await repo.list_statements(
        bank_name=bank_name,
        account_number=account_number,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

    return {
        "success": True,
        "count": len(statements),
        "statements": statements,
    }


# =============================================================================
# GET /api/v1/banking/statements/{statement_id} — Statement detail
# =============================================================================

@router.get("/statements/{statement_id}")
async def get_statement_detail(
    request: Request,
    statement_id: str,
    category: Optional[str] = Query(None, description="Filter transactions by category"),
):
    """
    Get a stored statement with its transactions.

    Returns the statement header and all associated categorized transactions.
    """
    repo = _get_repo(request)
    if repo is None:
        raise HTTPException(
            status_code=503,
            detail="Storage is unavailable — database not connected",
        )

    statement = await repo.get_statement(statement_id)
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    transactions = await repo.get_transactions(
        statement_id, category=category,
    )

    return {
        "success": True,
        "statement": statement,
        "transactions": transactions,
        "transaction_count": len(transactions),
    }


# =============================================================================
# DELETE /api/v1/banking/statements/{statement_id} — Delete statement
# =============================================================================

@router.delete("/statements/{statement_id}")
async def delete_statement(
    request: Request,
    statement_id: str,
):
    """
    Delete a stored statement and all its transactions (cascade).
    """
    repo = _get_repo(request)
    if repo is None:
        raise HTTPException(
            status_code=503,
            detail="Storage is unavailable — database not connected",
        )

    deleted = await repo.delete_statement(statement_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Statement not found")

    return {
        "success": True,
        "message": f"Statement {statement_id} deleted",
    }


# =============================================================================
# GET /api/v1/banking/stats — Overview statistics
# =============================================================================

@router.get("/stats")
async def get_stats(request: Request):
    """
    Get overview statistics for stored banking data.

    Returns total counts of statements and transactions, bank breakdown,
    and last processing time.
    """
    repo = _get_repo(request)
    if repo is None:
        raise HTTPException(
            status_code=503,
            detail="Storage is unavailable — database not connected",
        )

    stats = await repo.get_stats()

    return {
        "success": True,
        **stats,
    }
