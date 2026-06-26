"""
Tests for TransactionCategorizer component.
"""

from components.transaction_categorizer import (
    CategorizedTransaction,
    TransactionCategorizer,
)
from config.merchant_database import lookup_merchant


# =============================================================================
# Merchant Database Lookup Tests
# =============================================================================

class TestMerchantLookup:
    """Tests for the merchant database lookup function."""

    def test_exact_match(self):
        result = lookup_merchant("GRAB FOOD")
        assert result is not None
        assert result.category == "food_dining"

    def test_substring_match(self):
        result = lookup_merchant("THANH TOAN THE - SHOPEE - DON 12345")
        assert result is not None
        assert result.category == "shopping"

    def test_case_insensitive(self):
        result = lookup_merchant("Highlands Coffee Q1")
        assert result is not None
        assert result.category == "food_dining"
        assert result.subcategory == "cafe"

    def test_no_match(self):
        result = lookup_merchant("SOME RANDOM VENDOR 12345")
        assert result is None

    def test_utilities_evn(self):
        result = lookup_merchant("EVN HCMC TIEN DIEN T04")
        assert result is not None
        assert result.category == "utilities"

    def test_transportation_grab(self):
        result = lookup_merchant("GRAB CAR TRIP 20250403")
        assert result is not None
        assert result.category == "transportation"

    def test_streaming_netflix(self):
        result = lookup_merchant("NETFLIX.COM")
        assert result is not None
        assert result.category == "entertainment"
        assert result.subcategory == "streaming"


# =============================================================================
# Rule-based Categorization Tests
# =============================================================================

class TestRuleBasedCategorization:
    """Tests for rule-based categorization logic."""

    def setup_method(self):
        self.categorizer = TransactionCategorizer(agent=None)

    def test_salary_detection_keyword(self):
        txn = {
            "description": "LUONG T04/2025 - CONG TY ABC",
            "credit_amount": 35000000,
        }
        result = self.categorizer.categorize_single(txn)
        assert result.category == "salary"
        assert result.category_method == "rule_based"
        assert result.category_confidence >= 0.9

    def test_salary_detection_pattern(self):
        txn = {
            "description": "LUONG THANG 04 - CTY XYZ",
            "credit_amount": 25000000,
        }
        result = self.categorizer.categorize_single(txn)
        assert result.category == "salary"

    def test_food_merchant_match(self):
        txn = {
            "description": "THANH TOAN THE - THE COFFEE HOUSE Q3",
            "debit_amount": 85000,
        }
        result = self.categorizer.categorize_single(txn)
        assert result.category == "food_dining"
        assert result.subcategory == "cafe"
        assert result.category_confidence >= 0.9

    def test_ecommerce_shopping(self):
        txn = {
            "description": "SHOPEE - DON HANG 250403ABC",
            "debit_amount": 550000,
        }
        result = self.categorizer.categorize_single(txn)
        assert result.category == "shopping"
        assert result.subcategory == "ecommerce"

    def test_bank_fee_detection(self):
        txn = {
            "description": "PHI SMS BANKING T04/2025",
            "debit_amount": 11000,
        }
        result = self.categorizer.categorize_single(txn)
        assert result.category == "fee_charge"

    def test_transfer_out_pattern(self):
        txn = {
            "description": "CK CHO NGUYEN THI B - TIEN THUE NHA",
            "debit_amount": 8000000,
        }
        result = self.categorizer.categorize_single(txn)
        # Could match transfer_out or rent_mortgage
        assert result.category in ("transfer_out", "rent_mortgage")

    def test_uncategorized_transaction(self):
        txn = {
            "description": "GD 20250403 REF 98765432",
            "debit_amount": 200000,
        }
        result = self.categorizer.categorize_single(txn)
        assert result.category == "other"
        assert result.category_method == "default"
        assert result.category_confidence == 0.0

    def test_debit_amount_preserved(self):
        txn = {
            "description": "GRAB CAR",
            "debit_amount": 45000,
            "balance": 10000000,
        }
        result = self.categorizer.categorize_single(txn)
        assert result.debit_amount == 45000
        assert result.balance == 10000000

    def test_credit_direction_for_salary(self):
        """Salary rules should only match credit transactions."""
        txn = {
            "description": "LUONG T04",
            "debit_amount": 1000000,  # debit, not credit
        }
        result = self.categorizer.categorize_single(txn)
        # Should NOT categorize as salary since direction is debit
        assert result.category != "salary"

    def test_utilities_keyword(self):
        txn = {
            "description": "THANH TOAN CUOC INTERNET FPT T04",
            "debit_amount": 250000,
        }
        result = self.categorizer.categorize_single(txn)
        assert result.category in ("utilities",)

    def test_interest_earned(self):
        txn = {
            "description": "LAI TIET KIEM KY HAN 6 THANG",
            "credit_amount": 3500000,
        }
        result = self.categorizer.categorize_single(txn)
        assert result.category == "interest_earned"


# =============================================================================
# Batch Categorization Tests (rule-based only)
# =============================================================================

class TestBatchCategorization:
    """Tests for batch categorization."""

    def setup_method(self):
        self.categorizer = TransactionCategorizer(agent=None)

    def test_batch_categorization(self):
        transactions = [
            {"description": "LUONG T04/2025", "credit_amount": 35000000},
            {"description": "GRAB FOOD", "debit_amount": 120000},
            {"description": "PHI SMS T04", "debit_amount": 11000},
            {"description": "RANDOM GD 12345", "debit_amount": 50000},
        ]
        result = self.categorizer.categorize(
            transactions, use_llm_fallback=False
        )

        assert result.success is True
        assert len(result.transactions) == 4
        assert result.transactions[0].category == "salary"
        assert result.transactions[1].category == "food_dining"
        assert result.transactions[2].category == "fee_charge"
        assert result.transactions[3].category == "other"

    def test_summary_generation(self):
        transactions = [
            {"description": "LUONG", "credit_amount": 30000000},
            {"description": "GRAB", "debit_amount": 100000},
            {"description": "SHOPEE", "debit_amount": 500000},
        ]
        result = self.categorizer.categorize(
            transactions, use_llm_fallback=False
        )

        assert result.summary is not None
        assert result.summary["total_transactions"] == 3
        assert result.summary["total_income"] == 30000000
        assert result.summary["total_expense"] == 600000
        assert result.summary["net_flow"] == 29400000
        assert result.summary["auto_categorization_rate"] > 0

    def test_empty_transactions(self):
        result = self.categorizer.categorize([], use_llm_fallback=False)
        assert result.success is True
        assert len(result.transactions) == 0

    def test_single_transaction(self):
        result = self.categorizer.categorize(
            [{"description": "NETFLIX", "debit_amount": 260000}],
            use_llm_fallback=False,
        )
        assert result.success is True
        assert len(result.transactions) == 1
        assert result.transactions[0].category == "entertainment"


# =============================================================================
# Analytics Tests
# =============================================================================

class TestAnalytics:
    """Tests for BankingAnalyticsService."""

    def setup_method(self):
        from services.banking_analytics_service import BankingAnalyticsService
        self.service = BankingAnalyticsService()

    def test_basic_analytics(self):
        header = {
            "bank_name": "Vietcombank",
            "account_number": "0011004567890",
            "account_holder": "NGUYEN VAN A",
            "currency": "VND",
            "opening_balance": 10000000,
            "closing_balance": 39400000,
        }
        txns = [
            CategorizedTransaction(
                description="LUONG", credit_amount=30000000,
                category="salary", category_method="rule_based",
            ),
            CategorizedTransaction(
                description="GRAB", debit_amount=100000,
                category="transportation", category_method="rule_based",
            ),
            CategorizedTransaction(
                description="SHOPEE", debit_amount=500000,
                category="shopping", category_method="rule_based",
            ),
        ]

        report = self.service.analyze(header, txns)

        assert report.success is True
        assert report.cash_flow["total_income"] == 30000000
        assert report.cash_flow["total_expense"] == 600000
        assert report.cash_flow["net_flow"] == 29400000
        assert report.account_info["bank_name"] == "Vietcombank"
        assert report.account_info["account_number"].endswith("7890")

    def test_spending_breakdown(self):
        txns = [
            CategorizedTransaction(
                description="GRAB 1", debit_amount=50000,
                category="transportation",
            ),
            CategorizedTransaction(
                description="GRAB 2", debit_amount=70000,
                category="transportation",
            ),
            CategorizedTransaction(
                description="SHOPEE", debit_amount=300000,
                category="shopping",
            ),
        ]

        report = self.service.analyze({}, txns)

        assert report.spending_breakdown is not None
        assert len(report.spending_breakdown) == 2
        # Shopping should be first (higher amount)
        assert report.spending_breakdown[0]["category"] == "shopping"
        assert report.spending_breakdown[0]["amount"] == 300000
        assert report.spending_breakdown[1]["category"] == "transportation"
        assert report.spending_breakdown[1]["amount"] == 120000

    def test_empty_transactions(self):
        report = self.service.analyze({}, [])
        assert report.success is True
        assert report.cash_flow["total_income"] == 0
        assert report.cash_flow["total_expense"] == 0

    def test_account_masking(self):
        header = {"account_number": "0011004567890"}
        report = self.service.analyze(header, [])
        assert report.account_info["account_number"] == "*********7890"
