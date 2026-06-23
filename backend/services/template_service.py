"""
Template Service — CRUD and management for extraction templates.

Templates define reusable extraction schemas for specific document types.
Once a template is created, it can be auto-matched to incoming documents
and applied without manual configuration.

Storage: In-memory with optional PostgreSQL persistence (via workflow_repo).
Built-in templates are loaded on initialization.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Template Model
# =============================================================================


class ExtractionTemplate:
    """An extraction template definition."""

    def __init__(
        self,
        template_id: str = "",
        name: str = "",
        description: str = "",
        document_type: str = "",
        version: int = 1,
        match_rules: Optional[Dict[str, Any]] = None,
        extraction_schema: Optional[Dict[str, Any]] = None,
        processing_config: Optional[Dict[str, Any]] = None,
        is_builtin: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.template_id = template_id or uuid.uuid4().hex[:16]
        self.name = name
        self.description = description
        self.document_type = document_type
        self.version = version
        self.match_rules = match_rules or {}
        self.extraction_schema = extraction_schema or {"fields": []}
        self.processing_config = processing_config or {"tier": "Normal", "language": "vi"}
        self.is_builtin = is_builtin
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "document_type": self.document_type,
            "version": self.version,
            "match_rules": self.match_rules,
            "extraction_schema": self.extraction_schema,
            "processing_config": self.processing_config,
            "is_builtin": self.is_builtin,
            "field_count": len(self.extraction_schema.get("fields", [])),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractionTemplate":
        return cls(
            template_id=data.get("template_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            document_type=data.get("document_type", ""),
            version=data.get("version", 1),
            match_rules=data.get("match_rules", {}),
            extraction_schema=data.get("extraction_schema", {"fields": []}),
            processing_config=data.get("processing_config", {}),
            is_builtin=data.get("is_builtin", False),
        )


# =============================================================================
# Built-in Templates
# =============================================================================


def _builtin_templates() -> List[ExtractionTemplate]:
    """Create built-in templates for common document types."""
    return [
        ExtractionTemplate(
            template_id="builtin-invoice-vn",
            name="Hóa đơn Việt Nam",
            description="Template cho hóa đơn VAT Việt Nam (GTGT)",
            document_type="invoice",
            match_rules={
                "keywords": ["hóa đơn", "invoice", "mã số thuế", "GTGT", "giá trị gia tăng"],
                "classification_rules": [{"doc_type": "invoice", "description": "Hóa đơn giá trị gia tăng"}],
            },
            extraction_schema={
                "fields": [
                    {"field_name": "invoice_number", "field_type": "text", "description": "Số hóa đơn"},
                    {"field_name": "invoice_date", "field_type": "text", "description": "Ngày xuất hóa đơn"},
                    {"field_name": "seller_name", "field_type": "text", "description": "Tên đơn vị bán hàng"},
                    {"field_name": "seller_tax_id", "field_type": "text", "description": "Mã số thuế người bán"},
                    {"field_name": "buyer_name", "field_type": "text", "description": "Tên đơn vị mua hàng"},
                    {"field_name": "buyer_tax_id", "field_type": "text", "description": "Mã số thuế người mua"},
                    {"field_name": "subtotal", "field_type": "number", "description": "Cộng tiền hàng"},
                    {"field_name": "vat_rate", "field_type": "text", "description": "Thuế suất VAT (%)"},
                    {"field_name": "vat_amount", "field_type": "number", "description": "Tiền thuế GTGT"},
                    {"field_name": "total_amount", "field_type": "number", "description": "Tổng cộng tiền thanh toán"},
                ],
            },
            processing_config={"tier": "Normal", "language": "vi", "ocr_postprocess": True},
            is_builtin=True,
        ),
        ExtractionTemplate(
            template_id="builtin-receipt",
            name="Receipt / Biên lai",
            description="Template cho receipt, biên lai mua hàng",
            document_type="receipt",
            match_rules={
                "keywords": ["receipt", "biên lai", "total", "store", "cửa hàng", "thanh toán"],
                "classification_rules": [{"doc_type": "receipt", "description": "Biên lai mua hàng"}],
            },
            extraction_schema={
                "fields": [
                    {"field_name": "store_name", "field_type": "text", "description": "Tên cửa hàng"},
                    {"field_name": "store_address", "field_type": "text", "description": "Địa chỉ"},
                    {"field_name": "date", "field_type": "text", "description": "Ngày mua hàng"},
                    {"field_name": "total", "field_type": "number", "description": "Tổng tiền"},
                    {"field_name": "payment_method", "field_type": "text", "description": "Phương thức thanh toán"},
                ],
            },
            processing_config={"tier": "Rapid", "language": "vi"},
            is_builtin=True,
        ),
        ExtractionTemplate(
            template_id="builtin-id-card",
            name="ID Card / CCCD",
            description="Template cho căn cước công dân, CMND, passport",
            document_type="id_card",
            match_rules={
                "keywords": ["căn cước", "CCCD", "CMND", "citizen", "identity", "passport", "ID card"],
                "classification_rules": [{"doc_type": "id_card", "description": "Căn cước công dân / CMND"}],
            },
            extraction_schema={
                "fields": [
                    {"field_name": "full_name", "field_type": "text", "description": "Họ và tên"},
                    {"field_name": "id_number", "field_type": "text", "description": "Số CCCD/CMND"},
                    {"field_name": "date_of_birth", "field_type": "text", "description": "Ngày sinh"},
                    {"field_name": "gender", "field_type": "text", "description": "Giới tính"},
                    {"field_name": "nationality", "field_type": "text", "description": "Quốc tịch"},
                    {"field_name": "place_of_origin", "field_type": "text", "description": "Quê quán"},
                    {"field_name": "place_of_residence", "field_type": "text", "description": "Nơi thường trú"},
                    {"field_name": "expiry_date", "field_type": "text", "description": "Có giá trị đến"},
                ],
            },
            processing_config={"tier": "Normal", "language": "vi", "ocr_postprocess": True},
            is_builtin=True,
        ),
        ExtractionTemplate(
            template_id="builtin-bank-statement",
            name="Bank Statement / Sao kê ngân hàng",
            description="Template cho sao kê tài khoản ngân hàng",
            document_type="bank_statement",
            match_rules={
                "keywords": ["sao kê", "bank statement", "account", "tài khoản", "giao dịch", "transaction"],
                "classification_rules": [{"doc_type": "bank_statement", "description": "Sao kê ngân hàng"}],
            },
            extraction_schema={
                "fields": [
                    {"field_name": "account_number", "field_type": "text", "description": "Số tài khoản"},
                    {"field_name": "account_holder", "field_type": "text", "description": "Chủ tài khoản"},
                    {"field_name": "bank_name", "field_type": "text", "description": "Tên ngân hàng"},
                    {"field_name": "period_from", "field_type": "text", "description": "Từ ngày"},
                    {"field_name": "period_to", "field_type": "text", "description": "Đến ngày"},
                    {"field_name": "opening_balance", "field_type": "number", "description": "Số dư đầu kỳ"},
                    {"field_name": "closing_balance", "field_type": "number", "description": "Số dư cuối kỳ"},
                    {"field_name": "total_credit", "field_type": "number", "description": "Tổng tiền vào"},
                    {"field_name": "total_debit", "field_type": "number", "description": "Tổng tiền ra"},
                ],
            },
            processing_config={"tier": "Normal", "language": "vi"},
            is_builtin=True,
        ),
        ExtractionTemplate(
            template_id="builtin-contract",
            name="Contract / Hợp đồng",
            description="Template cho hợp đồng kinh tế, lao động",
            document_type="contract",
            match_rules={
                "keywords": ["hợp đồng", "contract", "agreement", "bên A", "bên B", "party"],
                "classification_rules": [{"doc_type": "contract", "description": "Hợp đồng"}],
            },
            extraction_schema={
                "fields": [
                    {"field_name": "contract_number", "field_type": "text", "description": "Số hợp đồng"},
                    {"field_name": "contract_date", "field_type": "text", "description": "Ngày ký"},
                    {"field_name": "party_a", "field_type": "text", "description": "Bên A (tên)"},
                    {"field_name": "party_b", "field_type": "text", "description": "Bên B (tên)"},
                    {"field_name": "contract_value", "field_type": "number", "description": "Giá trị hợp đồng"},
                    {"field_name": "effective_date", "field_type": "text", "description": "Ngày hiệu lực"},
                    {"field_name": "expiry_date", "field_type": "text", "description": "Ngày hết hạn"},
                ],
            },
            processing_config={"tier": "Advance", "language": "vi"},
            is_builtin=True,
        ),
        ExtractionTemplate(
            template_id="builtin-resume",
            name="Resume / CV",
            description="Template cho CV, hồ sơ xin việc",
            document_type="resume",
            match_rules={
                "keywords": ["resume", "CV", "curriculum vitae", "kinh nghiệm", "experience", "education", "skills"],
                "classification_rules": [{"doc_type": "resume", "description": "CV / Hồ sơ xin việc"}],
            },
            extraction_schema={
                "fields": [
                    {"field_name": "full_name", "field_type": "text", "description": "Họ và tên"},
                    {"field_name": "email", "field_type": "text", "description": "Email"},
                    {"field_name": "phone", "field_type": "text", "description": "Số điện thoại"},
                    {"field_name": "education", "field_type": "text", "description": "Học vấn"},
                    {"field_name": "experience", "field_type": "text", "description": "Kinh nghiệm làm việc"},
                    {"field_name": "skills", "field_type": "text", "description": "Kỹ năng"},
                    {"field_name": "objective", "field_type": "text", "description": "Mục tiêu nghề nghiệp"},
                ],
            },
            processing_config={"tier": "Advance", "language": "vi"},
            is_builtin=True,
        ),
    ]


# =============================================================================
# Template Service
# =============================================================================


class TemplateService:
    """
    Manages extraction templates (CRUD + search).

    Templates stored in-memory with built-ins loaded on init.
    Can optionally persist to PostgreSQL via workflow_repo.
    """

    def __init__(self):
        self._templates: Dict[str, ExtractionTemplate] = {}
        self._load_builtins()

    def _load_builtins(self) -> None:
        """Load built-in templates."""
        for t in _builtin_templates():
            self._templates[t.template_id] = t
        logger.info("TemplateService: loaded %d built-in templates", len(self._templates))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        document_type: str,
        extraction_schema: Dict[str, Any],
        description: str = "",
        match_rules: Optional[Dict[str, Any]] = None,
        processing_config: Optional[Dict[str, Any]] = None,
    ) -> ExtractionTemplate:
        """Create a new template."""
        template = ExtractionTemplate(
            name=name,
            description=description,
            document_type=document_type,
            match_rules=match_rules or {},
            extraction_schema=extraction_schema,
            processing_config=processing_config or {"tier": "Normal", "language": "vi"},
        )
        self._templates[template.template_id] = template
        logger.info("Template created: %s (%s)", template.name, template.template_id)
        return template

    def get(self, template_id: str) -> Optional[ExtractionTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def update(
        self,
        template_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        document_type: Optional[str] = None,
        match_rules: Optional[Dict[str, Any]] = None,
        extraction_schema: Optional[Dict[str, Any]] = None,
        processing_config: Optional[Dict[str, Any]] = None,
    ) -> Optional[ExtractionTemplate]:
        """Update an existing template. Returns None if not found."""
        template = self._templates.get(template_id)
        if template is None:
            return None
        if template.is_builtin:
            # Don't allow modifying built-ins directly, create a copy
            logger.warning("Cannot modify built-in template %s", template_id)
            return None

        if name is not None:
            template.name = name
        if description is not None:
            template.description = description
        if document_type is not None:
            template.document_type = document_type
        if match_rules is not None:
            template.match_rules = match_rules
        if extraction_schema is not None:
            template.extraction_schema = extraction_schema
        if processing_config is not None:
            template.processing_config = processing_config

        template.version += 1
        template.updated_at = datetime.now(timezone.utc)
        return template

    def delete(self, template_id: str) -> bool:
        """Delete a template. Cannot delete built-ins."""
        template = self._templates.get(template_id)
        if template is None:
            return False
        if template.is_builtin:
            return False
        del self._templates[template_id]
        return True

    def list_all(
        self,
        document_type: Optional[str] = None,
        include_builtin: bool = True,
    ) -> List[ExtractionTemplate]:
        """List all templates, optionally filtered."""
        templates = list(self._templates.values())

        if not include_builtin:
            templates = [t for t in templates if not t.is_builtin]

        if document_type:
            templates = [t for t in templates if t.document_type == document_type]

        return sorted(templates, key=lambda t: t.name)

    def search(self, query: str) -> List[ExtractionTemplate]:
        """Search templates by name, description, or document_type."""
        query_lower = query.lower()
        results = []
        for t in self._templates.values():
            if (
                query_lower in t.name.lower()
                or query_lower in t.description.lower()
                or query_lower in t.document_type.lower()
            ):
                results.append(t)
        return results

    @property
    def count(self) -> int:
        return len(self._templates)


# Module-level singleton
template_service = TemplateService()
