"""
Banking Data Mining - Schemas, Rules & Workflow Templates.

This module centralizes all banking-specific configurations:
- Classification rules for 10 banking document types
- Extraction schemas (header + transaction line items)
- Pre-built workflow templates
- Vietnamese-optimized extraction prompts

Usage:
    from config.banking_schemas import (
        BANKING_CLASSIFICATION_RULES,
        BANK_STATEMENT_HEADER_SCHEMA,
        BANK_STATEMENT_TRANSACTION_SCHEMA,
        get_workflow_template,
    )
"""

from __future__ import annotations

from typing import Any, Dict, List


# =============================================================================
# CLASSIFICATION RULES
# =============================================================================
# Used with POST /classify endpoint to identify banking document types.

BANKING_CLASSIFICATION_RULES: List[Dict[str, str]] = [
    {
        "doc_type": "bank_statement",
        "description": (
            "Sao kê tài khoản ngân hàng hàng tháng với danh sách giao dịch, "
            "số dư đầu/cuối kỳ, thông tin tài khoản và chi nhánh"
        ),
    },
    {
        "doc_type": "credit_card_statement",
        "description": (
            "Bảng kê chi tiêu thẻ tín dụng với thông tin merchant, "
            "dư nợ, hạn mức, hạn thanh toán tối thiểu"
        ),
    },
    {
        "doc_type": "loan_agreement",
        "description": (
            "Hợp đồng tín dụng/vay vốn với lãi suất, kỳ hạn, "
            "lịch trả nợ, tài sản đảm bảo"
        ),
    },
    {
        "doc_type": "kyc_document",
        "description": (
            "Giấy tờ tùy thân (CMND, CCCD, hộ chiếu) hoặc "
            "giấy tờ xác minh danh tính khách hàng"
        ),
    },
    {
        "doc_type": "check_deposit",
        "description": "Séc ngân hàng hoặc phiếu nộp/rút tiền mặt",
    },
    {
        "doc_type": "transfer_confirmation",
        "description": (
            "Biên lai xác nhận chuyển khoản với mã giao dịch, "
            "tài khoản nguồn/đích, số tiền, thời gian"
        ),
    },
    {
        "doc_type": "financial_report",
        "description": (
            "Báo cáo tài chính doanh nghiệp (bảng cân đối kế toán, "
            "kết quả kinh doanh, lưu chuyển tiền tệ)"
        ),
    },
    {
        "doc_type": "insurance_document",
        "description": (
            "Hợp đồng bảo hiểm với quyền lợi, phí bảo hiểm, thời hạn"
        ),
    },
    {
        "doc_type": "mortgage_document",
        "description": (
            "Hợp đồng thế chấp tài sản với thông tin định giá, "
            "điều kiện giải chấp"
        ),
    },
    {
        "doc_type": "tax_document",
        "description": (
            "Tờ khai thuế hoặc biên lai nộp thuế với mã số thuế, "
            "kỳ kê khai, số thuế phải nộp"
        ),
    },
]


# =============================================================================
# EXTRACTION SCHEMAS
# =============================================================================

# ---------------------------------------------------------------------------
# Schema 1: Bank Statement
# ---------------------------------------------------------------------------

BANK_STATEMENT_HEADER_SCHEMA: Dict[str, Any] = {
    "target": "document",
    "fields": [
        {"name": "bank_name", "type": "string", "description": "Tên ngân hàng phát hành sao kê", "required": True},
        {"name": "branch_name", "type": "string", "description": "Tên chi nhánh/phòng giao dịch", "required": False},
        {"name": "account_number", "type": "string", "description": "Số tài khoản (giữ nguyên format gốc)", "required": True},
        {"name": "account_holder", "type": "string", "description": "Tên chủ tài khoản", "required": True},
        {"name": "account_type", "type": "string", "description": "Loại tài khoản (thanh toán/tiết kiệm/vãng lai)", "required": False},
        {"name": "currency", "type": "string", "description": "Đơn vị tiền tệ (VND, USD, EUR)", "required": True},
        {"name": "statement_period_start", "type": "date", "description": "Ngày bắt đầu kỳ sao kê", "required": True},
        {"name": "statement_period_end", "type": "date", "description": "Ngày kết thúc kỳ sao kê", "required": True},
        {"name": "opening_balance", "type": "number", "description": "Số dư đầu kỳ", "required": True},
        {"name": "closing_balance", "type": "number", "description": "Số dư cuối kỳ", "required": True},
        {"name": "total_credit", "type": "number", "description": "Tổng tiền ghi có (tiền vào)", "required": False},
        {"name": "total_debit", "type": "number", "description": "Tổng tiền ghi nợ (tiền ra)", "required": False},
        {"name": "transaction_count", "type": "number", "description": "Tổng số giao dịch trong kỳ", "required": False},
    ],
}

BANK_STATEMENT_TRANSACTION_SCHEMA: Dict[str, Any] = {
    "target": "table_row",
    "fields": [
        {"name": "transaction_date", "type": "date", "description": "Ngày giao dịch", "required": True},
        {"name": "value_date", "type": "date", "description": "Ngày hiệu lực (ngày giá trị)", "required": False},
        {"name": "description", "type": "string", "description": "Nội dung/mô tả giao dịch", "required": True},
        {"name": "reference_number", "type": "string", "description": "Số tham chiếu/mã giao dịch", "required": False},
        {"name": "debit_amount", "type": "number", "description": "Số tiền ghi nợ (tiền ra), null nếu là giao dịch ghi có", "required": False},
        {"name": "credit_amount", "type": "number", "description": "Số tiền ghi có (tiền vào), null nếu là giao dịch ghi nợ", "required": False},
        {"name": "balance", "type": "number", "description": "Số dư sau giao dịch", "required": False},
        {"name": "transaction_type", "type": "string", "description": "Loại giao dịch (transfer/payment/withdrawal/deposit/fee/interest)", "required": False},
        {"name": "counterparty", "type": "string", "description": "Tên đối tác giao dịch (người gửi/nhận)", "required": False},
        {"name": "counterparty_account", "type": "string", "description": "Số tài khoản đối tác", "required": False},
        {"name": "counterparty_bank", "type": "string", "description": "Ngân hàng đối tác", "required": False},
    ],
}

# ---------------------------------------------------------------------------
# Schema 2: Credit Card Statement
# ---------------------------------------------------------------------------

CREDIT_CARD_HEADER_SCHEMA: Dict[str, Any] = {
    "target": "document",
    "fields": [
        {"name": "bank_name", "type": "string", "description": "Ngân hàng phát hành thẻ", "required": True},
        {"name": "card_number_masked", "type": "string", "description": "Số thẻ (đã che, ví dụ: **** **** **** 1234)", "required": True},
        {"name": "card_holder", "type": "string", "description": "Tên chủ thẻ", "required": True},
        {"name": "card_type", "type": "string", "description": "Loại thẻ (Visa/Mastercard/JCB/Amex)", "required": False},
        {"name": "credit_limit", "type": "number", "description": "Hạn mức tín dụng", "required": False},
        {"name": "available_credit", "type": "number", "description": "Hạn mức khả dụng còn lại", "required": False},
        {"name": "statement_date", "type": "date", "description": "Ngày sao kê", "required": True},
        {"name": "payment_due_date", "type": "date", "description": "Ngày đến hạn thanh toán", "required": True},
        {"name": "previous_balance", "type": "number", "description": "Dư nợ kỳ trước", "required": False},
        {"name": "new_charges", "type": "number", "description": "Tổng chi tiêu phát sinh trong kỳ", "required": True},
        {"name": "payments_received", "type": "number", "description": "Tổng thanh toán đã nhận", "required": False},
        {"name": "current_balance", "type": "number", "description": "Dư nợ hiện tại", "required": True},
        {"name": "minimum_payment", "type": "number", "description": "Số tiền thanh toán tối thiểu", "required": True},
        {"name": "interest_rate", "type": "number", "description": "Lãi suất áp dụng (%/năm)", "required": False},
        {"name": "interest_charged", "type": "number", "description": "Tiền lãi phát sinh trong kỳ", "required": False},
    ],
}

CREDIT_CARD_TRANSACTION_SCHEMA: Dict[str, Any] = {
    "target": "table_row",
    "fields": [
        {"name": "transaction_date", "type": "date", "description": "Ngày giao dịch", "required": True},
        {"name": "posting_date", "type": "date", "description": "Ngày hạch toán", "required": False},
        {"name": "merchant_name", "type": "string", "description": "Tên merchant/đơn vị chấp nhận thẻ", "required": True},
        {"name": "merchant_category", "type": "string", "description": "Danh mục merchant (MCC description)", "required": False},
        {"name": "amount_original", "type": "number", "description": "Số tiền gốc (ngoại tệ nếu có)", "required": True},
        {"name": "original_currency", "type": "string", "description": "Đơn vị tiền gốc (USD, EUR, VND...)", "required": False},
        {"name": "amount_billed", "type": "number", "description": "Số tiền quy đổi (VND)", "required": True},
        {"name": "transaction_type", "type": "string", "description": "Loại (purchase/refund/cash_advance/fee/interest)", "required": False},
    ],
}

# ---------------------------------------------------------------------------
# Schema 3: Loan Agreement
# ---------------------------------------------------------------------------

LOAN_AGREEMENT_SCHEMA: Dict[str, Any] = {
    "target": "document",
    "fields": [
        {"name": "contract_number", "type": "string", "description": "Số hợp đồng tín dụng", "required": True},
        {"name": "contract_date", "type": "date", "description": "Ngày ký hợp đồng", "required": True},
        {"name": "lender_name", "type": "string", "description": "Tên bên cho vay (ngân hàng)", "required": True},
        {"name": "borrower_name", "type": "string", "description": "Tên bên vay", "required": True},
        {"name": "borrower_id", "type": "string", "description": "Số CMND/CCCD bên vay", "required": False},
        {"name": "loan_amount", "type": "number", "description": "Số tiền vay", "required": True},
        {"name": "currency", "type": "string", "description": "Đơn vị tiền tệ", "required": True},
        {"name": "interest_rate", "type": "number", "description": "Lãi suất (%/năm)", "required": True},
        {"name": "interest_type", "type": "string", "description": "Loại lãi suất (fixed/floating/mixed)", "required": False},
        {"name": "loan_term_months", "type": "number", "description": "Kỳ hạn vay (tháng)", "required": True},
        {"name": "disbursement_date", "type": "date", "description": "Ngày giải ngân", "required": False},
        {"name": "maturity_date", "type": "date", "description": "Ngày đáo hạn", "required": True},
        {"name": "repayment_method", "type": "string", "description": "Phương thức trả nợ (equal_principal/equal_installment/bullet)", "required": False},
        {"name": "collateral_description", "type": "string", "description": "Mô tả tài sản đảm bảo", "required": False},
        {"name": "collateral_value", "type": "number", "description": "Giá trị tài sản đảm bảo", "required": False},
        {"name": "loan_purpose", "type": "string", "description": "Mục đích vay vốn", "required": False},
    ],
}

# ---------------------------------------------------------------------------
# Schema 4: Transfer Confirmation
# ---------------------------------------------------------------------------

TRANSFER_CONFIRMATION_SCHEMA: Dict[str, Any] = {
    "target": "document",
    "fields": [
        {"name": "transaction_id", "type": "string", "description": "Mã giao dịch / số tham chiếu", "required": True},
        {"name": "transaction_datetime", "type": "string", "description": "Ngày giờ giao dịch (format: YYYY-MM-DD HH:mm:ss)", "required": True},
        {"name": "sender_name", "type": "string", "description": "Tên người chuyển", "required": True},
        {"name": "sender_account", "type": "string", "description": "Số tài khoản người chuyển", "required": True},
        {"name": "sender_bank", "type": "string", "description": "Ngân hàng người chuyển", "required": False},
        {"name": "receiver_name", "type": "string", "description": "Tên người nhận", "required": True},
        {"name": "receiver_account", "type": "string", "description": "Số tài khoản người nhận", "required": True},
        {"name": "receiver_bank", "type": "string", "description": "Ngân hàng người nhận", "required": False},
        {"name": "amount", "type": "number", "description": "Số tiền chuyển", "required": True},
        {"name": "fee", "type": "number", "description": "Phí chuyển khoản", "required": False},
        {"name": "transfer_content", "type": "string", "description": "Nội dung chuyển khoản", "required": False},
        {"name": "status", "type": "string", "description": "Trạng thái giao dịch (success/pending/failed)", "required": False},
    ],
}

# ---------------------------------------------------------------------------
# Schema 5: KYC Document
# ---------------------------------------------------------------------------

KYC_DOCUMENT_SCHEMA: Dict[str, Any] = {
    "target": "document",
    "fields": [
        {"name": "document_type", "type": "string", "description": "Loại giấy tờ (cmnd/cccd/passport/driving_license)", "required": True},
        {"name": "document_number", "type": "string", "description": "Số giấy tờ", "required": True},
        {"name": "full_name", "type": "string", "description": "Họ và tên đầy đủ", "required": True},
        {"name": "date_of_birth", "type": "date", "description": "Ngày sinh", "required": True},
        {"name": "gender", "type": "string", "description": "Giới tính (male/female)", "required": False},
        {"name": "nationality", "type": "string", "description": "Quốc tịch", "required": False},
        {"name": "place_of_origin", "type": "string", "description": "Quê quán / nơi sinh", "required": False},
        {"name": "permanent_address", "type": "string", "description": "Địa chỉ thường trú", "required": False},
        {"name": "issue_date", "type": "date", "description": "Ngày cấp", "required": True},
        {"name": "expiry_date", "type": "date", "description": "Ngày hết hạn", "required": False},
        {"name": "issuing_authority", "type": "string", "description": "Nơi cấp / cơ quan cấp", "required": False},
    ],
}


# =============================================================================
# SCHEMA REGISTRY
# =============================================================================
# Map document types to their extraction schemas for automatic routing.

SCHEMA_REGISTRY: Dict[str, Dict[str, Any]] = {
    "bank_statement": {
        "header": BANK_STATEMENT_HEADER_SCHEMA,
        "transactions": BANK_STATEMENT_TRANSACTION_SCHEMA,
    },
    "credit_card_statement": {
        "header": CREDIT_CARD_HEADER_SCHEMA,
        "transactions": CREDIT_CARD_TRANSACTION_SCHEMA,
    },
    "loan_agreement": {
        "document": LOAN_AGREEMENT_SCHEMA,
    },
    "transfer_confirmation": {
        "document": TRANSFER_CONFIRMATION_SCHEMA,
    },
    "kyc_document": {
        "document": KYC_DOCUMENT_SCHEMA,
    },
}


def get_schema_for_doc_type(doc_type: str) -> Dict[str, Any] | None:
    """
    Get extraction schema(s) for a given document type.

    Args:
        doc_type: Document type string from classification result.

    Returns:
        Dictionary of schema name -> schema definition, or None if not found.
    """
    return SCHEMA_REGISTRY.get(doc_type)


# =============================================================================
# SUPPORTED VIETNAMESE BANKS
# =============================================================================

SUPPORTED_BANKS: List[Dict[str, str]] = [
    {"code": "VCB", "name": "Vietcombank", "formats": "PDF"},
    {"code": "BIDV", "name": "BIDV", "formats": "PDF, Excel"},
    {"code": "CTG", "name": "VietinBank", "formats": "PDF"},
    {"code": "TCB", "name": "Techcombank", "formats": "PDF, Image"},
    {"code": "MBB", "name": "MB Bank", "formats": "PDF"},
    {"code": "ACB", "name": "ACB", "formats": "PDF"},
    {"code": "VPB", "name": "VPBank", "formats": "PDF"},
    {"code": "TPB", "name": "TPBank", "formats": "PDF, Image"},
    {"code": "STB", "name": "Sacombank", "formats": "PDF"},
    {"code": "HDB", "name": "HDBank", "formats": "PDF"},
]


# =============================================================================
# WORKFLOW TEMPLATES
# =============================================================================

def _build_extract_step(schema: Dict[str, Any], tier: str = "Advance") -> Dict[str, Any]:
    """Build an extract step from a schema definition."""
    return {
        "type": "extract",
        "tier": tier,
        "config": {
            "target": schema["target"],
            "schema": {"fields": schema["fields"]},
        },
    }


WORKFLOW_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "full_bank_statement_mining": {
        "name": "full_bank_statement_mining",
        "description": "Khai thác toàn bộ dữ liệu từ sao kê ngân hàng (header + giao dịch)",
        "steps": [
            {"type": "parse", "tier": "Advance", "config": {}},
            {
                "type": "classify",
                "tier": "Normal",
                "config": {
                    "rules": [
                        {"doc_type": "bank_statement", "description": "Sao kê tài khoản ngân hàng"},
                        {"doc_type": "credit_card_statement", "description": "Sao kê thẻ tín dụng"},
                        {"doc_type": "transfer_confirmation", "description": "Biên lai chuyển khoản"},
                        {"doc_type": "other", "description": "Tài liệu khác"},
                    ],
                },
            },
            _build_extract_step(BANK_STATEMENT_HEADER_SCHEMA),
            _build_extract_step(BANK_STATEMENT_TRANSACTION_SCHEMA),
        ],
    },
    "credit_card_mining": {
        "name": "credit_card_mining",
        "description": "Trích xuất chi tiêu từ sao kê thẻ tín dụng",
        "steps": [
            {"type": "parse", "tier": "Advance", "config": {}},
            _build_extract_step(CREDIT_CARD_HEADER_SCHEMA),
            _build_extract_step(CREDIT_CARD_TRANSACTION_SCHEMA),
        ],
    },
    "kyc_processing": {
        "name": "kyc_processing",
        "description": "Trích xuất thông tin từ giấy tờ tùy thân",
        "steps": [
            {"type": "parse", "tier": "Advance", "config": {}},
            {
                "type": "classify",
                "tier": "Normal",
                "config": {
                    "rules": [
                        {"doc_type": "cmnd", "description": "Chứng minh nhân dân (9 hoặc 12 số)"},
                        {"doc_type": "cccd", "description": "Căn cước công dân (có chip hoặc không)"},
                        {"doc_type": "passport", "description": "Hộ chiếu Việt Nam hoặc quốc tế"},
                        {"doc_type": "driving_license", "description": "Giấy phép lái xe"},
                        {"doc_type": "business_license", "description": "Giấy phép đăng ký kinh doanh"},
                    ],
                },
            },
            _build_extract_step(KYC_DOCUMENT_SCHEMA),
        ],
    },
    "loan_analysis": {
        "name": "loan_analysis",
        "description": "Trích xuất thông tin từ hợp đồng tín dụng",
        "steps": [
            {"type": "parse", "tier": "Advance", "config": {}},
            _build_extract_step(LOAN_AGREEMENT_SCHEMA),
        ],
    },
    "transfer_confirmation": {
        "name": "transfer_confirmation",
        "description": "Trích xuất thông tin từ biên lai chuyển khoản",
        "steps": [
            {"type": "parse", "tier": "Advance", "config": {}},
            _build_extract_step(TRANSFER_CONFIRMATION_SCHEMA),
        ],
    },
}


def get_workflow_template(template_name: str) -> Dict[str, Any] | None:
    """
    Get a pre-built workflow template by name.

    Args:
        template_name: Template name (e.g. "full_bank_statement_mining").

    Returns:
        Workflow definition dict, or None if not found.
    """
    return WORKFLOW_TEMPLATES.get(template_name)


def list_workflow_templates() -> List[Dict[str, str]]:
    """List available workflow templates with names and descriptions."""
    return [
        {"name": wf["name"], "description": wf["description"]}
        for wf in WORKFLOW_TEMPLATES.values()
    ]


# =============================================================================
# VIETNAMESE EXTRACTION PROMPTS
# =============================================================================
# Optimized prompts for Vietnamese banking documents.

BANKING_EXTRACTION_PROMPTS: Dict[str, str] = {
    "bank_statement_header": (
        "Trích xuất thông tin header từ sao kê ngân hàng Việt Nam. "
        "Chú ý: số tài khoản giữ nguyên format gốc, số tiền không có dấu chấm "
        "phân cách hàng nghìn (ví dụ: 15000000 thay vì 15.000.000), "
        "ngày tháng theo format YYYY-MM-DD. "
        "Đơn vị tiền tệ mặc định là VND nếu không ghi rõ."
    ),
    "bank_statement_transactions": (
        "Trích xuất TẤT CẢ các dòng giao dịch từ bảng sao kê. "
        "Mỗi dòng giao dịch là một object trong mảng JSON. "
        "Số tiền ghi nợ (debit) là tiền ra, ghi có (credit) là tiền vào. "
        "Nếu cột ghi nợ trống thì debit_amount = null (không phải 0). "
        "Giữ nguyên nội dung mô tả giao dịch bằng tiếng Việt."
    ),
    "credit_card": (
        "Trích xuất thông tin từ sao kê thẻ tín dụng. "
        "Số thẻ giữ dạng masked (ví dụ: **** 1234). "
        "Phân biệt số tiền gốc (ngoại tệ) và số tiền quy đổi VND."
    ),
    "kyc": (
        "Trích xuất thông tin từ giấy tờ tùy thân Việt Nam. "
        "Số CMND/CCCD giữ nguyên format. "
        "Ngày sinh, ngày cấp theo format YYYY-MM-DD. "
        "Họ tên viết HOA đúng theo giấy tờ gốc."
    ),
}
