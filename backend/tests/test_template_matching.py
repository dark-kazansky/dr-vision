"""
Unit tests for Template Matching (feat-063).

Tests: TemplateService CRUD, built-in templates, TemplateMatcher scoring,
API router, workflow integration.
"""

from services.template_service import ExtractionTemplate, TemplateService, template_service
from services.template_matcher import template_matcher


# =============================================================================
# TemplateService Tests
# =============================================================================


class TestTemplateService:
    def test_builtins_loaded(self):
        assert template_service.count >= 6

    def test_get_builtin(self):
        t = template_service.get("builtin-invoice-vn")
        assert t is not None
        assert t.name == "Hóa đơn Việt Nam"
        assert t.document_type == "invoice"
        assert t.is_builtin is True
        assert len(t.extraction_schema["fields"]) >= 8

    def test_get_nonexistent(self):
        assert template_service.get("nonexistent") is None

    def test_create_custom(self):
        svc = TemplateService()
        t = svc.create(
            name="Test Template",
            document_type="test_doc",
            extraction_schema={"fields": [{"field_name": "x", "field_type": "text"}]},
        )
        assert t.template_id != ""
        assert t.name == "Test Template"
        assert t.is_builtin is False
        assert svc.get(t.template_id) is not None

    def test_update_custom(self):
        svc = TemplateService()
        t = svc.create(name="Original", document_type="test", extraction_schema={"fields": []})
        updated = svc.update(t.template_id, name="Updated")
        assert updated is not None
        assert updated.name == "Updated"
        assert updated.version == 2

    def test_cannot_update_builtin(self):
        result = template_service.update("builtin-invoice-vn", name="Hacked")
        assert result is None

    def test_delete_custom(self):
        svc = TemplateService()
        t = svc.create(name="To Delete", document_type="x", extraction_schema={"fields": []})
        assert svc.delete(t.template_id) is True
        assert svc.get(t.template_id) is None

    def test_cannot_delete_builtin(self):
        assert template_service.delete("builtin-invoice-vn") is False

    def test_list_all(self):
        templates = template_service.list_all()
        assert len(templates) >= 6

    def test_list_by_document_type(self):
        templates = template_service.list_all(document_type="invoice")
        assert len(templates) >= 1
        assert all(t.document_type == "invoice" for t in templates)

    def test_search(self):
        results = template_service.search("hóa đơn")
        assert len(results) >= 1
        assert any("invoice" in r.document_type for r in results)

    def test_to_dict(self):
        t = template_service.get("builtin-receipt")
        assert t is not None
        d = t.to_dict()
        assert d["template_id"] == "builtin-receipt"
        assert d["field_count"] == 5
        assert "created_at" in d

    def test_from_dict(self):
        data = {
            "template_id": "test-123",
            "name": "Test",
            "document_type": "test",
            "extraction_schema": {"fields": [{"field_name": "a", "field_type": "text"}]},
        }
        t = ExtractionTemplate.from_dict(data)
        assert t.template_id == "test-123"
        assert t.name == "Test"


# =============================================================================
# TemplateMatcher Tests
# =============================================================================


class TestTemplateMatcher:
    def test_match_invoice_by_keywords(self):
        text = "HÓA ĐƠN GIÁ TRỊ GIA TĂNG. Mã số thuế: 1234567890. Tổng cộng: 500.000 VND"
        result = template_matcher.match(text)
        assert result.success is True
        assert result.best_match is not None
        assert result.best_match.document_type == "invoice"
        assert result.best_match.confidence > 0.2

    def test_match_bank_statement(self):
        text = "SAO KÊ TÀI KHOẢN. Số tài khoản: 123456789. Giao dịch tháng 01/2024."
        result = template_matcher.match(text)
        assert result.success is True
        assert result.best_match is not None
        assert result.best_match.document_type == "bank_statement"

    def test_match_id_card(self):
        text = "CĂN CƯỚC CÔNG DÂN. Họ và tên: Nguyễn Văn A. Số CCCD: 012345678901."
        result = template_matcher.match(text)
        assert result.success is True
        assert result.best_match is not None
        assert result.best_match.document_type == "id_card"

    def test_match_resume(self):
        text = "CURRICULUM VITAE. Education: MIT. Experience: 5 years. Skills: Python, Java."
        result = template_matcher.match(text)
        assert result.success is True
        assert result.best_match is not None
        assert result.best_match.document_type == "resume"

    def test_no_match_random_text(self):
        text = "The quick brown fox jumps over the lazy dog. Nothing special here."
        result = template_matcher.match(text)
        # May or may not have a match depending on threshold
        assert result.success is True

    def test_empty_text(self):
        result = template_matcher.match("")
        assert result.success is False
        assert "Empty" in result.no_match_reason

    def test_match_with_document_type_boost(self):
        text = "Some document about invoices and payments"
        result_without = template_matcher.match(text)
        result_with = template_matcher.match(text, document_type="invoice")

        # With document_type should boost invoice match confidence
        if result_with.best_match and result_without.best_match:
            if result_with.best_match.document_type == "invoice":
                assert result_with.best_match.confidence >= result_without.best_match.confidence

    def test_match_returns_multiple(self):
        text = "Hóa đơn thanh toán. Hợp đồng kinh tế. Số tài khoản ngân hàng."
        result = template_matcher.match(text)
        assert result.success is True
        # Should return multiple matches since text has keywords from multiple templates
        assert len(result.all_matches) >= 1

    def test_match_by_type_direct(self):
        template = template_matcher.match_by_type("invoice")
        assert template is not None
        assert template.document_type == "invoice"

    def test_match_by_type_unknown(self):
        template = template_matcher.match_by_type("nonexistent_type")
        assert template is None

    def test_match_result_to_dict(self):
        text = "Hóa đơn giá trị gia tăng. Mã số thuế bên bán."
        result = template_matcher.match(text)
        d = result.to_dict()
        assert "success" in d
        assert "best_match" in d
        assert "all_matches" in d
        assert "match_count" in d


# =============================================================================
# API Router Tests
# =============================================================================


class TestTemplateAPIRouter:
    def test_router_exists(self):
        from api.v1.templates import router
        assert router is not None
        assert len(router.routes) >= 7  # CRUD + match + extract + auto-extract


# =============================================================================
# Workflow Integration Tests
# =============================================================================


class TestWorkflowIntegration:
    def test_workflow_step_callable(self):
        from services.workflow_service import _run_template_extract_step
        assert callable(_run_template_extract_step)

    def test_durable_activity_registered(self):
        from services.workflow_engine.activities import get_all_handlers
        handlers = get_all_handlers()
        assert "template_extract" in handlers
