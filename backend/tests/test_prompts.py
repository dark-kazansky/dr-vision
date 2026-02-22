"""
Test prompts module.

Tests the centralized prompt templates for different model types and tasks.
"""

import pytest
from core.prompts import (
    PromptTemplates, ModelType, TaskType,
    get_ocr_prompt, get_classify_prompt, get_extract_prompt, get_split_prompt,
    get_system_prompt
)


class TestModelTypeDetection:
    """Test model type detection from provider names."""
    
    def test_detect_vlm_providers(self):
        """Test VLM provider detection."""
        assert PromptTemplates.detect_model_type('google_studio') == ModelType.VLM
        assert PromptTemplates.detect_model_type('google') == ModelType.VLM
        assert PromptTemplates.detect_model_type('poe_vision') == ModelType.VLM
    
    def test_detect_llm_providers(self):
        """Test LLM provider detection."""
        assert PromptTemplates.detect_model_type('poe_api') == ModelType.LLM
        assert PromptTemplates.detect_model_type('poe') == ModelType.LLM
        assert PromptTemplates.detect_model_type('ollama') == ModelType.LLM
    
    def test_detect_ocr_providers(self):
        """Test OCR provider detection."""
        assert PromptTemplates.detect_model_type('lm_studio') == ModelType.OCR
        assert PromptTemplates.detect_model_type('lmstudio') == ModelType.OCR
        assert PromptTemplates.detect_model_type('vllm') == ModelType.OCR
        assert PromptTemplates.detect_model_type('lightonocr_api') == ModelType.OCR


class TestOCRPrompts:
    """Test OCR prompt generation."""
    
    def test_vlm_ocr_prompt(self):
        """Test VLM OCR prompt."""
        prompt = PromptTemplates.get_ocr_prompt(ModelType.VLM)
        assert "Extract all text from this image" in prompt
        assert "vision" not in prompt.lower() or "image" in prompt.lower()
        assert "Return only the extracted text" in prompt
    
    def test_llm_ocr_prompt(self):
        """Test LLM OCR prompt."""
        prompt = PromptTemplates.get_ocr_prompt(ModelType.LLM)
        assert "OCR" in prompt
        assert "assistant" in prompt.lower() or "extract" in prompt.lower()
    
    def test_ocr_model_prompt(self):
        """Test dedicated OCR model prompt."""
        prompt = PromptTemplates.get_ocr_prompt(ModelType.OCR)
        assert len(prompt) > 0
        assert "extract" in prompt.lower() or "text" in prompt.lower()
    
    def test_ocr_prompt_with_language(self):
        """Test OCR prompt with language specification."""
        prompt = PromptTemplates.get_ocr_prompt(ModelType.VLM, language="English")
        assert "English" in prompt
    
    def test_convenience_function(self):
        """Test convenience function for OCR prompts."""
        prompt = get_ocr_prompt('google_studio')
        assert len(prompt) > 0
        assert "extract" in prompt.lower() or "text" in prompt.lower()


class TestClassifyPrompts:
    """Test classification prompt generation."""
    
    def test_vlm_classify_prompt(self):
        """Test VLM classification prompt."""
        doc_types = [
            {"doc_type": "invoice", "description": "Commercial invoice"},
            {"doc_type": "receipt", "description": "Payment receipt"}
        ]
        prompt = PromptTemplates.get_classify_prompt(ModelType.VLM, doc_types)
        assert "invoice" in prompt
        assert "receipt" in prompt
        assert "JSON" in prompt
        assert "document_type" in prompt
    
    def test_llm_classify_prompt(self):
        """Test LLM classification prompt."""
        doc_types = [
            {"doc_type": "contract", "description": "Legal contract"}
        ]
        text = "This is a sample contract text"
        prompt = PromptTemplates.get_classify_prompt(ModelType.LLM, doc_types, text=text)
        assert "contract" in prompt
        assert "sample contract" in prompt
        assert "JSON" in prompt
    
    def test_ocr_classify_error(self):
        """Test that OCR models return error for classification."""
        doc_types = [{"doc_type": "test", "description": "Test"}]
        prompt = PromptTemplates.get_classify_prompt(ModelType.OCR, doc_types)
        assert "ERROR" in prompt
    
    def test_convenience_function(self):
        """Test convenience function for classification prompts."""
        doc_types = [{"doc_type": "invoice", "description": "Invoice"}]
        prompt = get_classify_prompt('poe_api', doc_types)
        assert "invoice" in prompt


class TestExtractPrompts:
    """Test extraction prompt generation."""
    
    def test_vlm_extract_prompt(self):
        """Test VLM extraction prompt."""
        schema_fields = [
            {"name": "vendor_name", "type": "string", "description": "Vendor name", "required": True},
            {"name": "total", "type": "number", "description": "Total amount", "required": False}
        ]
        prompt = PromptTemplates.get_extract_prompt(ModelType.VLM, schema_fields)
        assert "vendor_name" in prompt
        assert "total" in prompt
        assert "REQUIRED" in prompt
        assert "JSON" in prompt
    
    def test_llm_extract_prompt(self):
        """Test LLM extraction prompt."""
        schema_fields = [
            {"name": "date", "type": "date", "description": "Invoice date", "required": True}
        ]
        text = "Invoice dated 2024-01-15"
        prompt = PromptTemplates.get_extract_prompt(ModelType.LLM, schema_fields, text=text)
        assert "date" in prompt
        assert "2024-01-15" in prompt
        assert "JSON" in prompt
    
    def test_extract_with_target(self):
        """Test extraction prompt with different targets."""
        schema_fields = [{"name": "field", "type": "string", "required": False}]
        
        prompt_doc = PromptTemplates.get_extract_prompt(ModelType.VLM, schema_fields, target="document")
        assert "entire document" in prompt_doc
        
        prompt_page = PromptTemplates.get_extract_prompt(ModelType.VLM, schema_fields, target="page")
        assert "each page" in prompt_page
    
    def test_convenience_function(self):
        """Test convenience function for extraction prompts."""
        schema_fields = [{"name": "name", "type": "string", "required": True}]
        prompt = get_extract_prompt('google', schema_fields)
        assert "name" in prompt


class TestSplitPrompts:
    """Test splitting prompt generation."""
    
    def test_vlm_split_prompt(self):
        """Test VLM splitting prompt."""
        categories = [
            {"name": "header", "description": "Document header"},
            {"name": "body", "description": "Main content"}
        ]
        prompt = PromptTemplates.get_split_prompt(ModelType.VLM, categories)
        assert "header" in prompt
        assert "body" in prompt
        assert "chunks" in prompt
        assert "JSON" in prompt
    
    def test_llm_split_prompt(self):
        """Test LLM splitting prompt."""
        categories = [
            {"name": "intro", "description": "Introduction section"}
        ]
        prompt = PromptTemplates.get_split_prompt(ModelType.LLM, categories)
        assert "intro" in prompt
        assert "chunks" in prompt
    
    def test_split_with_uncategorized(self):
        """Test splitting prompt with uncategorized option."""
        categories = [{"name": "test", "description": "Test category"}]
        
        prompt_allow = PromptTemplates.get_split_prompt(ModelType.VLM, categories, allow_uncategorized=True)
        assert "unknown" in prompt_allow
        
        prompt_disallow = PromptTemplates.get_split_prompt(ModelType.VLM, categories, allow_uncategorized=False)
        assert "must be assigned" in prompt_disallow
    
    def test_convenience_function(self):
        """Test convenience function for splitting prompts."""
        categories = [{"name": "section", "description": "Section"}]
        prompt = get_split_prompt('google_studio', categories)
        assert "section" in prompt


class TestSystemPrompts:
    """Test system prompt generation."""
    
    def test_vlm_system_prompts(self):
        """Test VLM system prompts for all tasks."""
        ocr_prompt = PromptTemplates.get_system_prompt(ModelType.VLM, TaskType.OCR)
        assert ocr_prompt is not None
        assert "OCR" in ocr_prompt or "vision" in ocr_prompt.lower()
        
        classify_prompt = PromptTemplates.get_system_prompt(ModelType.VLM, TaskType.CLASSIFY)
        assert classify_prompt is not None
        assert "classification" in classify_prompt.lower() or "categorize" in classify_prompt.lower()
    
    def test_llm_system_prompts(self):
        """Test LLM system prompts for all tasks."""
        extract_prompt = PromptTemplates.get_system_prompt(ModelType.LLM, TaskType.EXTRACT)
        assert extract_prompt is not None
        assert "extract" in extract_prompt.lower() or "data" in extract_prompt.lower()
    
    def test_ocr_system_prompt(self):
        """Test OCR model system prompt (should be None)."""
        prompt = PromptTemplates.get_system_prompt(ModelType.OCR, TaskType.OCR)
        assert prompt is None
    
    def test_convenience_function(self):
        """Test convenience function for system prompts."""
        prompt = get_system_prompt('poe_api', 'classify')
        assert prompt is not None


class TestPromptFormatting:
    """Test prompt formatting utilities."""
    
    def test_format_with_context(self):
        """Test formatting prompt with context."""
        base_prompt = "Extract data"
        context = {
            "language": "English",
            "format": "JSON",
            "instructions": "Be precise"
        }
        formatted = PromptTemplates.format_prompt_with_context(base_prompt, context)
        assert "Extract data" in formatted
        assert "English" in formatted
        assert "JSON" in formatted
        assert "Be precise" in formatted
    
    def test_format_without_context(self):
        """Test formatting prompt without context."""
        base_prompt = "Extract data"
        formatted = PromptTemplates.format_prompt_with_context(base_prompt)
        assert formatted == base_prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
