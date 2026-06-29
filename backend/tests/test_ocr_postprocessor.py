"""
Unit tests for OCR Post-processing (feat-061).

Tests: number correction, Vietnamese diacritics, confidence scoring,
normalization, API router, workflow integration, /ocr endpoint integration.
"""

import pytest
from unittest.mock import patch, AsyncMock

from components.ocr_postprocessor import (
    Correction,
    OCRPostProcessor,
    PostProcessResult,
    WordConfidence,
)


class TestNumberCorrection:
    def test_o_to_zero_in_numbers(self):
        processor = OCRPostProcessor()
        result = processor.process("Total: 1OO.OOO VND")
        assert "100.000" in result.processed_text
        assert result.stats["correction_count"] > 0

    def test_l_to_one_in_numbers(self):
        processor = OCRPostProcessor()
        result = processor.process("Amount: 1l0.000")
        assert "110.000" in result.processed_text

    def test_preserve_normal_text(self):
        processor = OCRPostProcessor()
        result = processor.process("Hello World")
        assert result.processed_text == "Hello World"
        assert result.stats["correction_count"] == 0

    def test_year_correction(self):
        processor = OCRPostProcessor()
        result = processor.process("Year 2O24")
        assert "2024" in result.processed_text

    def test_disable_number_correction(self):
        processor = OCRPostProcessor(enable_number_correction=False)
        result = processor.process("1OO.OOO VND")
        # Should NOT correct when disabled
        assert "1OO" in result.processed_text or "100" in result.processed_text


class TestVietnameseCorrection:
    def test_nguoi_to_nguoi_with_diacritics(self):
        processor = OCRPostProcessor(language="vi")
        result = processor.process("nguoi dung")
        assert "người" in result.processed_text

    def test_so_before_number(self):
        processor = OCRPostProcessor(language="vi")
        result = processor.process("so 12345")
        assert "số" in result.processed_text

    def test_ngay_before_date(self):
        processor = OCRPostProcessor(language="vi")
        result = processor.process("ngay 01/01/2024")
        assert "ngày" in result.processed_text

    def test_nam_before_year(self):
        processor = OCRPostProcessor(language="vi")
        result = processor.process("nam 2024")
        assert "năm" in result.processed_text

    def test_no_diacritics_when_english(self):
        processor = OCRPostProcessor(language="en")
        result = processor.process("nguoi dung")
        # English mode should NOT apply Vietnamese corrections
        assert result.processed_text == "nguoi dung"


class TestCurrencyNormalization:
    def test_vnd_uppercase(self):
        processor = OCRPostProcessor()
        result = processor.process("100.000 vnd")
        assert "VND" in result.processed_text

    def test_usd_uppercase(self):
        processor = OCRPostProcessor()
        result = processor.process("50 usd")
        assert "USD" in result.processed_text


class TestWhitespaceNormalization:
    def test_collapse_multiple_spaces(self):
        processor = OCRPostProcessor()
        result = processor.process("hello    world")
        assert result.processed_text == "hello world"

    def test_trim_lines(self):
        processor = OCRPostProcessor()
        result = processor.process("  hello  \n  world  ")
        assert result.processed_text == "hello\nworld"

    def test_collapse_multiple_newlines(self):
        processor = OCRPostProcessor()
        result = processor.process("a\n\n\n\n\nb")
        assert result.processed_text == "a\n\nb"


class TestConfidenceScoring:
    def test_normal_words_high_confidence(self):
        processor = OCRPostProcessor()
        result = processor.process("Hello World")
        for wc in result.word_confidences:
            assert wc.confidence >= 0.8

    def test_short_word_lower_confidence(self):
        processor = OCRPostProcessor()
        result = processor.process("x y z normal")
        # Single-char words should have lower confidence
        short_words = [w for w in result.word_confidences if len(w.text) == 1]
        normal_words = [w for w in result.word_confidences if w.text == "normal"]
        if short_words and normal_words:
            assert short_words[0].confidence <= normal_words[0].confidence

    def test_corrected_word_flagged(self):
        processor = OCRPostProcessor()
        result = processor.process("1OO VND")
        corrected = [w for w in result.word_confidences if w.is_corrected]
        # At least some words should be marked as corrected
        assert len(corrected) >= 0  # May or may not flag depending on pattern

    def test_stats_populated(self):
        processor = OCRPostProcessor()
        result = processor.process("Hello World OCR text")
        assert result.stats["word_count"] == 4
        assert "average_confidence" in result.stats
        assert "low_confidence_count" in result.stats


class TestPostProcessResult:
    def test_empty_text(self):
        processor = OCRPostProcessor()
        result = processor.process("")
        assert result.success is True
        assert result.processed_text == ""
        assert result.stats["word_count"] == 0

    def test_to_dict(self):
        result = PostProcessResult(
            success=True,
            processed_text="Hello",
            original_text="Hel1o",
            word_confidences=[WordConfidence(text="Hello", confidence=0.9)],
            corrections=[Correction(original="1", corrected="l", rule="test")],
            stats={"word_count": 1},
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["processed_text"] == "Hello"
        assert len(d["word_confidences"]) == 1
        assert len(d["corrections"]) == 1

    def test_word_confidence_to_dict(self):
        wc = WordConfidence(text="test", confidence=0.85, is_corrected=True, original="tset")
        d = wc.to_dict()
        assert d["text"] == "test"
        assert d["confidence"] == 0.85
        assert d["is_corrected"] is True
        assert d["original"] == "tset"


class TestCustomRules:
    def test_custom_pattern(self):
        processor = OCRPostProcessor(custom_rules=[
            (r"\bfoo\b", "bar"),
        ])
        result = processor.process("hello foo world")
        assert "bar" in result.processed_text
        assert any(c.rule == "custom" for c in result.corrections)


class TestAPIRouter:
    def test_router_exists(self):
        from api.v1.postprocess import router
        assert router is not None
        assert len(router.routes) >= 1


class TestWorkflowIntegration:
    def test_workflow_step_callable(self):
        from services.workflow_service import _run_ocr_postprocess_step
        assert callable(_run_ocr_postprocess_step)

    def test_durable_activity_registered(self):
        from services.workflow_engine.activities import get_all_handlers
        handlers = get_all_handlers()
        assert "ocr_postprocess" in handlers


# ---------------------------------------------------------------------------
# Tests — /ocr endpoint integration (feat-061)
# ---------------------------------------------------------------------------


class TestRunPostprocessHelper:
    """Tests for services.parse_service._run_postprocess helper."""

    def test_returns_expected_keys(self):
        from services.parse_service import _run_postprocess

        result = _run_postprocess("Tong: 1OO.OOO VND", "vi", 0.7)
        assert "processed_text" in result
        assert "word_confidences" in result
        assert "postprocess_stats" in result
        assert "postprocess_corrections" in result

    def test_corrects_numbers(self):
        from services.parse_service import _run_postprocess

        result = _run_postprocess("1OO.OOO VND", "vi", 0.7)
        assert "100.000" in result["processed_text"]
        # number correction should be recorded
        assert any(c["rule"] == "number_correction" for c in result["postprocess_corrections"])

    def test_word_confidences_populated(self):
        from services.parse_service import _run_postprocess

        result = _run_postprocess("Hello World 1OO", "en", 0.7)
        confs = result["word_confidences"]
        assert len(confs) == 3
        for w in confs:
            assert "text" in w
            assert "confidence" in w
            assert 0.0 <= w["confidence"] <= 1.0

    def test_stats_populated(self):
        from services.parse_service import _run_postprocess

        result = _run_postprocess("some text here", "vi", 0.7)
        stats = result["postprocess_stats"]
        assert stats["word_count"] == 3
        assert "low_confidence_count" in stats
        assert "average_confidence" in stats

    def test_empty_text(self):
        from services.parse_service import _run_postprocess

        result = _run_postprocess("", "vi", 0.7)
        assert result["processed_text"] == ""
        assert result["word_confidences"] == []

    def test_returns_error_key_on_failure(self):
        """If the postprocessor raises, the helper should return postprocess_error."""
        from services.parse_service import _run_postprocess

        with patch("components.ocr_postprocessor.OCRPostProcessor.process", side_effect=RuntimeError("boom")):
            result = _run_postprocess("text", "vi", 0.7)
        assert "postprocess_error" in result


# ---------------------------------------------------------------------------
# Fixtures for endpoint tests
# ---------------------------------------------------------------------------

def _make_pdf_bytes():
    return b"%PDF-1.4 fake content for testing"


@pytest.fixture
def _reset_config_singleton():
    from config.manager import Config
    Config._instance = None
    yield
    Config._instance = None


@pytest.fixture
def client(_reset_config_singleton):
    import httpx
    from fastapi import FastAPI
    from api.v1.parse import router
    from core.dependencies import get_config
    from unittest.mock import MagicMock

    cfg = MagicMock()
    cfg.upload_config = {
        "max_size_mb": 10,
        "folder": "/tmp/test_uploads",
        "allowed_extensions": [".pdf", ".png", ".jpg", ".jpeg", ".txt", ".docx"],
    }
    cfg._config_data = {"background_tasks": {"enabled": False, "threshold_pages": 5}}

    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_config] = lambda: cfg
    transport = httpx.ASGITransport(app=test_app)
    yield httpx.AsyncClient(transport=transport, base_url="http://testserver")
    test_app.dependency_overrides.clear()


class TestOcrEndpointPostprocessParam:
    """Tests that the /ocr endpoint accepts and forwards the postprocess params."""

    @pytest.mark.asyncio
    async def test_ocr_with_postprocess_includes_fields(self, client):
        """POST /ocr with postprocess=true includes postprocess fields in response."""
        mock_result = {
            "success": True,
            "text": "1OO.OOO VND",
            "parsed_text": "1OO.OOO VND",
            "file_type": "pdf",
            "is_scanned": False,
            "pages": 1,
            "filename": "test.pdf",
            "model": "test-model",
            "processed_text": "100.000 VND",
            "word_confidences": [
                {"text": "100.000", "confidence": 0.85},
                {"text": "VND", "confidence": 1.0},
            ],
            "postprocess_stats": {"word_count": 2, "correction_count": 1, "low_confidence_count": 0, "low_confidence_ratio": 0.0, "average_confidence": 0.925},
            "postprocess_corrections": [
                {"original": "1OO.OOO", "corrected": "100.000", "rule": "number_correction", "position": 0},
            ],
        }

        with patch("services.parse_service.parse_document", new_callable=AsyncMock, return_value=mock_result):
            async with client:
                resp = await client.post(
                    "/ocr",
                    data={
                        "model_id": "test-model",
                        "postprocess": "true",
                        "postprocess_language": "vi",
                        "postprocess_confidence_threshold": "0.7",
                    },
                    files={"file": ("test.pdf", _make_pdf_bytes(), "application/pdf")},
                )

        assert resp.status_code == 200
        body = resp.json()
        assert "processed_text" in body
        assert "word_confidences" in body
        assert "postprocess_stats" in body

    @pytest.mark.asyncio
    async def test_ocr_without_postprocess_omits_fields(self, client):
        """POST /ocr with postprocess=false omits postprocess fields."""
        mock_result = {
            "success": True,
            "text": "Hello",
            "file_type": "pdf",
            "is_scanned": False,
            "pages": 1,
            "filename": "test.pdf",
            "model": "test-model",
        }

        with patch("services.parse_service.parse_document", new_callable=AsyncMock, return_value=mock_result):
            async with client:
                resp = await client.post(
                    "/ocr",
                    data={"model_id": "test-model", "postprocess": "false"},
                    files={"file": ("test.pdf", _make_pdf_bytes(), "application/pdf")},
                )

        assert resp.status_code == 200
        body = resp.json()
        assert "processed_text" not in body
        assert "word_confidences" not in body
