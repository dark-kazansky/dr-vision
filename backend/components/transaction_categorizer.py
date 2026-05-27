"""
Transaction Categorizer — Hybrid rule-based + LLM categorization.

Categorizes bank transactions into spending categories using a two-step approach:
1. Rule-based matching (keywords, patterns, merchant database) — fast, high confidence
2. LLM fallback — for transactions that rules cannot categorize

Follows the same component pattern as Classifier:
    categorizer = TransactionCategorizer(agent=llm_agent)
    result = categorizer.categorize(transactions)

Usage:
    from components.transaction_categorizer import TransactionCategorizer
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agents import BaseLLMAgent
from config.merchant_database import CATEGORY_RULES, lookup_merchant
from core.utils import strip_code_blocks

logger = logging.getLogger(__name__)


# =============================================================================
# Data classes
# =============================================================================

@dataclass
class CategorizedTransaction:
    """A single transaction with category information attached."""
    transaction_date: Optional[str] = None
    description: str = ""
    debit_amount: Optional[float] = None
    credit_amount: Optional[float] = None
    balance: Optional[float] = None
    category: str = "other"
    category_confidence: float = 0.0
    category_method: str = "unclassified"  # rule_based | llm | default
    subcategory: str = ""
    # Pass-through: keep any extra fields from the original transaction
    extra_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CategorizeResult:
    """Result of a categorization operation."""
    success: bool
    transactions: List[CategorizedTransaction] = field(default_factory=list)
    summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


# =============================================================================
# Categorizer
# =============================================================================

# Known fields that map directly to CategorizedTransaction attributes.
_KNOWN_FIELDS = {
    "transaction_date", "description", "debit_amount", "credit_amount",
    "balance", "category", "category_confidence", "category_method",
    "subcategory",
}

# Categories available for LLM classification prompt.
_ALL_CATEGORIES = [
    ("salary", "Lương & thu nhập"),
    ("transfer_in", "Chuyển khoản đến"),
    ("transfer_out", "Chuyển khoản đi"),
    ("food_dining", "Ăn uống"),
    ("groceries", "Siêu thị & tạp hóa"),
    ("transportation", "Di chuyển"),
    ("utilities", "Tiện ích (điện, nước, internet)"),
    ("rent_mortgage", "Nhà ở"),
    ("healthcare", "Y tế"),
    ("education", "Giáo dục"),
    ("entertainment", "Giải trí"),
    ("shopping", "Mua sắm"),
    ("insurance", "Bảo hiểm"),
    ("investment", "Đầu tư"),
    ("loan_payment", "Trả nợ vay"),
    ("fee_charge", "Phí ngân hàng"),
    ("interest_earned", "Lãi tiết kiệm"),
    ("other", "Khác"),
]


class TransactionCategorizer:
    """
    Hybrid transaction categorizer: rule-based first, LLM fallback.

    Args:
        agent: Optional LLM agent for fallback categorization.
               If None, only rule-based matching is used.
    """

    def __init__(self, agent: Optional[BaseLLMAgent] = None):
        self.agent = agent

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def categorize(
        self,
        transactions: List[Dict[str, Any]],
        use_llm_fallback: bool = True,
        confidence_threshold: float = 0.7,
        timeout: int = 60,
    ) -> CategorizeResult:
        """
        Categorize a list of transactions.

        Args:
            transactions: List of transaction dicts (from extraction result).
            use_llm_fallback: Whether to use LLM for unmatched transactions.
            confidence_threshold: Minimum confidence to accept LLM result.
            timeout: LLM request timeout in seconds.

        Returns:
            CategorizeResult with categorized transactions and summary.
        """
        try:
            categorized: List[CategorizedTransaction] = []
            uncategorized_indices: List[int] = []

            # Step 1: Rule-based categorization
            for i, txn in enumerate(transactions):
                result = self._rule_based_categorize(txn)
                categorized.append(result)
                if result.category == "other":
                    uncategorized_indices.append(i)

            # Step 2: LLM fallback for uncategorized
            if use_llm_fallback and self.agent and uncategorized_indices:
                uncategorized_txns = [transactions[i] for i in uncategorized_indices]
                llm_results = self._llm_categorize_batch(
                    uncategorized_txns, confidence_threshold, timeout
                )
                for idx, llm_cat in zip(uncategorized_indices, llm_results):
                    if llm_cat.category != "other":
                        categorized[idx] = llm_cat

            # Build summary
            summary = self._build_summary(categorized)

            return CategorizeResult(
                success=True,
                transactions=categorized,
                summary=summary,
            )

        except Exception as e:
            logger.exception("Categorization failed")
            return CategorizeResult(
                success=False,
                error=f"Categorization failed: {str(e)}",
                error_type="processing_error",
            )

    def categorize_single(self, transaction: Dict[str, Any]) -> CategorizedTransaction:
        """Categorize a single transaction (rule-based only, no LLM)."""
        return self._rule_based_categorize(transaction)

    # ------------------------------------------------------------------
    # Rule-based categorization
    # ------------------------------------------------------------------

    def _rule_based_categorize(self, txn: Dict[str, Any]) -> CategorizedTransaction:
        """Apply rule-based categorization to a single transaction."""
        description = str(txn.get("description", ""))
        debit = txn.get("debit_amount")
        credit = txn.get("credit_amount")
        direction = "credit" if credit and not debit else "debit"

        # Extract known fields, store the rest in extra_fields
        cat_txn = CategorizedTransaction(
            transaction_date=txn.get("transaction_date"),
            description=description,
            debit_amount=_to_float(debit),
            credit_amount=_to_float(credit),
            balance=_to_float(txn.get("balance")),
        )
        for key, val in txn.items():
            if key not in _KNOWN_FIELDS:
                cat_txn.extra_fields[key] = val

        # 1) Merchant database lookup
        merchant = lookup_merchant(description)
        if merchant:
            cat_txn.category = merchant.category
            cat_txn.subcategory = merchant.subcategory
            cat_txn.category_confidence = 0.95
            cat_txn.category_method = "rule_based"
            return cat_txn

        # 2) Keyword + pattern matching
        desc_normalized = _normalize_vn(description)
        for category, rule in CATEGORY_RULES.items():
            # Direction filter
            if rule.get("direction") and rule["direction"] != direction:
                continue

            # Keyword match
            for kw in rule.get("keywords", []):
                if kw in desc_normalized:
                    cat_txn.category = category
                    cat_txn.category_confidence = 0.90
                    cat_txn.category_method = "rule_based"
                    return cat_txn

            # Regex pattern match
            for pattern in rule.get("patterns", []):
                if re.search(pattern, description, re.IGNORECASE):
                    cat_txn.category = category
                    cat_txn.category_confidence = 0.90
                    cat_txn.category_method = "rule_based"
                    return cat_txn

        # No match → "other"
        cat_txn.category = "other"
        cat_txn.category_confidence = 0.0
        cat_txn.category_method = "default"
        return cat_txn

    # ------------------------------------------------------------------
    # LLM-based categorization
    # ------------------------------------------------------------------

    def _llm_categorize_batch(
        self,
        transactions: List[Dict[str, Any]],
        confidence_threshold: float,
        timeout: int,
    ) -> List[CategorizedTransaction]:
        """Use LLM to categorize a batch of transactions."""
        results: List[CategorizedTransaction] = []

        # Build batch prompt (up to 20 transactions at a time)
        batch_size = 20
        for start in range(0, len(transactions), batch_size):
            batch = transactions[start:start + batch_size]
            prompt = self._build_llm_prompt(batch)

            try:
                response = self.agent.generate(prompt, timeout=timeout)
                if not response.success:
                    logger.warning("LLM categorization failed: %s", response.error)
                    results.extend(self._default_results(batch))
                    continue

                parsed = self._parse_llm_response(response.content, batch, confidence_threshold)
                results.extend(parsed)

            except Exception as e:
                logger.warning("LLM categorization error: %s", e)
                results.extend(self._default_results(batch))

        return results

    def _build_llm_prompt(self, transactions: List[Dict[str, Any]]) -> str:
        """Build LLM prompt for batch categorization."""
        categories_text = "\n".join(
            f"- {code}: {desc}" for code, desc in _ALL_CATEGORIES
        )

        txn_lines = []
        for i, txn in enumerate(transactions):
            desc = txn.get("description", "")
            amount = txn.get("debit_amount") or txn.get("credit_amount") or 0
            direction = "credit" if txn.get("credit_amount") else "debit"
            txn_lines.append(f"{i+1}. [{direction}] {amount:,.0f} — {desc}")

        txn_text = "\n".join(txn_lines)

        return f"""Phân loại các giao dịch ngân hàng Việt Nam sau vào danh mục phù hợp.

Danh mục:
{categories_text}

Giao dịch:
{txn_text}

Trả lời JSON array, mỗi phần tử có format:
{{"index": 1, "category": "mã_danh_mục", "confidence": 0.85}}

Chỉ trả lời JSON array, không giải thích thêm."""

    def _parse_llm_response(
        self,
        content: str,
        original_txns: List[Dict[str, Any]],
        confidence_threshold: float,
    ) -> List[CategorizedTransaction]:
        """Parse LLM categorization response."""
        results: List[CategorizedTransaction] = []
        try:
            cleaned = strip_code_blocks(content)
            data = json.loads(cleaned)
            if not isinstance(data, list):
                data = [data]

            # Index the LLM results by their index field
            llm_map: Dict[int, Dict] = {}
            for item in data:
                idx = item.get("index", 0) - 1  # Convert 1-based to 0-based
                if 0 <= idx < len(original_txns):
                    llm_map[idx] = item

            for i, txn in enumerate(original_txns):
                cat_txn = CategorizedTransaction(
                    transaction_date=txn.get("transaction_date"),
                    description=str(txn.get("description", "")),
                    debit_amount=_to_float(txn.get("debit_amount")),
                    credit_amount=_to_float(txn.get("credit_amount")),
                    balance=_to_float(txn.get("balance")),
                )

                if i in llm_map:
                    confidence = float(llm_map[i].get("confidence", 0))
                    category = llm_map[i].get("category", "other")
                    if confidence >= confidence_threshold:
                        cat_txn.category = category
                        cat_txn.category_confidence = confidence
                        cat_txn.category_method = "llm"
                    else:
                        cat_txn.category = "other"
                        cat_txn.category_confidence = confidence
                        cat_txn.category_method = "llm_low_confidence"
                else:
                    cat_txn.category = "other"
                    cat_txn.category_method = "default"

                results.append(cat_txn)

        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to parse LLM categorization response: %s", e)
            results = self._default_results(original_txns)

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _default_results(self, transactions: List[Dict[str, Any]]) -> List[CategorizedTransaction]:
        """Create default (uncategorized) results for a batch."""
        return [
            CategorizedTransaction(
                transaction_date=txn.get("transaction_date"),
                description=str(txn.get("description", "")),
                debit_amount=_to_float(txn.get("debit_amount")),
                credit_amount=_to_float(txn.get("credit_amount")),
                balance=_to_float(txn.get("balance")),
                category="other",
                category_method="default",
            )
            for txn in transactions
        ]

    @staticmethod
    def _build_summary(transactions: List[CategorizedTransaction]) -> Dict[str, Any]:
        """Build aggregated summary from categorized transactions."""
        total_income = 0.0
        total_expense = 0.0
        by_category: Dict[str, Dict[str, Any]] = {}
        methods = {"rule_based": 0, "llm": 0, "default": 0, "llm_low_confidence": 0}

        for txn in transactions:
            amount = txn.credit_amount or txn.debit_amount or 0
            if txn.credit_amount:
                total_income += txn.credit_amount
            if txn.debit_amount:
                total_expense += txn.debit_amount

            cat = txn.category
            if cat not in by_category:
                by_category[cat] = {"amount": 0.0, "count": 0}
            by_category[cat]["amount"] += amount
            by_category[cat]["count"] += 1

            method = txn.category_method
            if method in methods:
                methods[method] += 1

        total_count = len(transactions)
        auto_rate = (methods["rule_based"] + methods["llm"]) / total_count if total_count else 0

        return {
            "total_transactions": total_count,
            "total_income": total_income,
            "total_expense": total_expense,
            "net_flow": total_income - total_expense,
            "auto_categorization_rate": round(auto_rate, 3),
            "categorization_methods": methods,
            "by_category": [
                {
                    "category": cat,
                    "amount": round(info["amount"], 2),
                    "count": info["count"],
                    "percentage": round(info["amount"] / total_expense * 100, 1) if total_expense else 0,
                }
                for cat, info in sorted(by_category.items(), key=lambda x: x[1]["amount"], reverse=True)
            ],
        }


# =============================================================================
# Module-level helpers
# =============================================================================

def _normalize_vn(text: str) -> str:
    """Normalize Vietnamese text for keyword matching (lowercase, no diacritics)."""
    return text.lower().strip()


def _to_float(value: Any) -> Optional[float]:
    """Safely convert a value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
