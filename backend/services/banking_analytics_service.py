"""
Banking Analytics Service — Cash flow, spending analysis & reporting.

Provides analytical functions over categorized transaction data:
- Cash flow analysis (income vs expense over time)
- Spending breakdown by category
- Income source analysis
- Top merchants / counterparties
- Monthly trend comparison

Usage:
    from services.banking_analytics_service import BankingAnalyticsService

    analytics = BankingAnalyticsService()
    report = analytics.analyze(header, categorized_transactions)
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from components.transaction_categorizer import CategorizedTransaction

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsReport:
    """Complete analytics report for a set of transactions."""
    success: bool
    cash_flow: Optional[Dict[str, Any]] = None
    spending_breakdown: Optional[List[Dict[str, Any]]] = None
    income_breakdown: Optional[List[Dict[str, Any]]] = None
    top_expenses: Optional[List[Dict[str, Any]]] = None
    top_income_sources: Optional[List[Dict[str, Any]]] = None
    daily_flow: Optional[List[Dict[str, Any]]] = None
    account_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BankingAnalyticsService:
    """
    Stateless analytics service. All methods are pure functions over data.
    """

    def analyze(
        self,
        header: Dict[str, Any],
        transactions: List[CategorizedTransaction],
    ) -> AnalyticsReport:
        """
        Run a full analytics suite on categorized transactions.

        Args:
            header: Extracted statement header (bank_name, balances, period, etc.)
            transactions: List of CategorizedTransaction from TransactionCategorizer.

        Returns:
            AnalyticsReport with all analytical breakdowns.
        """
        try:
            cash_flow = self._cash_flow_analysis(header, transactions)
            spending = self._spending_breakdown(transactions)
            income = self._income_breakdown(transactions)
            top_exp = self._top_transactions(transactions, direction="debit", limit=10)
            top_inc = self._top_transactions(transactions, direction="credit", limit=10)
            daily = self._daily_flow(transactions)

            account_info = {
                "bank_name": header.get("bank_name"),
                "account_number": _mask_account(header.get("account_number", "")),
                "account_holder": header.get("account_holder"),
                "currency": header.get("currency", "VND"),
                "period_start": header.get("statement_period_start"),
                "period_end": header.get("statement_period_end"),
            }

            return AnalyticsReport(
                success=True,
                cash_flow=cash_flow,
                spending_breakdown=spending,
                income_breakdown=income,
                top_expenses=top_exp,
                top_income_sources=top_inc,
                daily_flow=daily,
                account_info=account_info,
            )

        except Exception as e:
            logger.exception("Analytics failed")
            return AnalyticsReport(success=False, error=str(e))

    # ------------------------------------------------------------------
    # Cash flow
    # ------------------------------------------------------------------

    def _cash_flow_analysis(
        self,
        header: Dict[str, Any],
        transactions: List[CategorizedTransaction],
    ) -> Dict[str, Any]:
        """Calculate overall cash flow metrics."""
        total_income = sum(t.credit_amount for t in transactions if t.credit_amount)
        total_expense = sum(t.debit_amount for t in transactions if t.debit_amount)
        net_flow = total_income - total_expense

        opening = header.get("opening_balance", 0) or 0
        closing = header.get("closing_balance", 0) or 0

        # Validate balance consistency
        expected_closing = opening + total_income - total_expense
        balance_matches = abs(expected_closing - closing) < 2  # allow rounding

        return {
            "total_income": round(total_income, 2),
            "total_expense": round(total_expense, 2),
            "net_flow": round(net_flow, 2),
            "opening_balance": opening,
            "closing_balance": closing,
            "balance_check": {
                "expected_closing": round(expected_closing, 2),
                "actual_closing": closing,
                "matches": balance_matches,
            },
            "income_count": sum(1 for t in transactions if t.credit_amount),
            "expense_count": sum(1 for t in transactions if t.debit_amount),
            "total_count": len(transactions),
            "savings_rate": round(net_flow / total_income * 100, 1) if total_income else 0,
        }

    # ------------------------------------------------------------------
    # Spending breakdown
    # ------------------------------------------------------------------

    def _spending_breakdown(
        self, transactions: List[CategorizedTransaction],
    ) -> List[Dict[str, Any]]:
        """Break down expenses by category."""
        by_cat: Dict[str, Dict] = defaultdict(lambda: {"amount": 0.0, "count": 0})

        total_expense = 0.0
        for t in transactions:
            if t.debit_amount:
                by_cat[t.category]["amount"] += t.debit_amount
                by_cat[t.category]["count"] += 1
                total_expense += t.debit_amount

        result = []
        for cat, info in sorted(by_cat.items(), key=lambda x: x[1]["amount"], reverse=True):
            result.append({
                "category": cat,
                "amount": round(info["amount"], 2),
                "count": info["count"],
                "percentage": round(info["amount"] / total_expense * 100, 1) if total_expense else 0,
            })

        return result

    # ------------------------------------------------------------------
    # Income breakdown
    # ------------------------------------------------------------------

    def _income_breakdown(
        self, transactions: List[CategorizedTransaction],
    ) -> List[Dict[str, Any]]:
        """Break down income by category."""
        by_cat: Dict[str, Dict] = defaultdict(lambda: {"amount": 0.0, "count": 0})

        total_income = 0.0
        for t in transactions:
            if t.credit_amount:
                by_cat[t.category]["amount"] += t.credit_amount
                by_cat[t.category]["count"] += 1
                total_income += t.credit_amount

        result = []
        for cat, info in sorted(by_cat.items(), key=lambda x: x[1]["amount"], reverse=True):
            result.append({
                "category": cat,
                "amount": round(info["amount"], 2),
                "count": info["count"],
                "percentage": round(info["amount"] / total_income * 100, 1) if total_income else 0,
            })

        return result

    # ------------------------------------------------------------------
    # Top transactions
    # ------------------------------------------------------------------

    def _top_transactions(
        self,
        transactions: List[CategorizedTransaction],
        direction: str = "debit",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get the largest transactions by amount."""
        if direction == "debit":
            filtered = [t for t in transactions if t.debit_amount]
            filtered.sort(key=lambda t: t.debit_amount or 0, reverse=True)
        else:
            filtered = [t for t in transactions if t.credit_amount]
            filtered.sort(key=lambda t: t.credit_amount or 0, reverse=True)

        return [
            {
                "date": t.transaction_date,
                "description": t.description,
                "amount": t.debit_amount if direction == "debit" else t.credit_amount,
                "category": t.category,
            }
            for t in filtered[:limit]
        ]

    # ------------------------------------------------------------------
    # Daily flow
    # ------------------------------------------------------------------

    def _daily_flow(
        self, transactions: List[CategorizedTransaction],
    ) -> List[Dict[str, Any]]:
        """Aggregate income/expense by day."""
        daily: Dict[str, Dict] = defaultdict(lambda: {"income": 0.0, "expense": 0.0})

        for t in transactions:
            date_key = t.transaction_date or "unknown"
            if t.credit_amount:
                daily[date_key]["income"] += t.credit_amount
            if t.debit_amount:
                daily[date_key]["expense"] += t.debit_amount

        result = []
        for date_key in sorted(daily.keys()):
            info = daily[date_key]
            result.append({
                "date": date_key,
                "income": round(info["income"], 2),
                "expense": round(info["expense"], 2),
                "net": round(info["income"] - info["expense"], 2),
            })

        return result


# =============================================================================
# Helpers
# =============================================================================

def _mask_account(account: str) -> str:
    """Mask account number for display (show last 4 digits)."""
    if not account or len(account) <= 4:
        return account
    return "*" * (len(account) - 4) + account[-4:]
