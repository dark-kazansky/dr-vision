"""
Centralized prompt templates for different model types and tasks.

This module provides prompts for:
- VLM (Vision-Language Models): Google Studio, POE Vision models
- LLM (Language Models): POE, Google Studio text models
- OCR (Optical Character Recognition): LM Studio, vLLM

Tasks supported:
- OCR: Extract text from images/documents
- Classify: Classify documents into categories
- Extract: Extract structured data from text
- Split: Split documents into categorized chunks
"""

from typing import Dict, List, Optional
from enum import Enum


class ModelType(str, Enum):
    """Model type enumeration."""
    VLM = "vlm"      # Vision-Language Model
    LLM = "llm"      # Language Model
    OCR = "ocr"      # OCR Model


class TaskType(str, Enum):
    """Task type enumeration."""
    OCR = "ocr"
    CLASSIFY = "classify"
    EXTRACT = "extract"
    SPLIT = "split"


class PromptTemplates:
    """
    Centralized prompt templates for different model types and tasks.
    """
    
    # =========================================================================
    # OCR TASK PROMPTS
    # =========================================================================
    
    @staticmethod
    def get_ocr_prompt(model_type: ModelType, **kwargs) -> str:
        """
        Get OCR prompt for extracting text from images/documents.
        
        Args:
            model_type: Type of model (VLM, LLM, OCR)
            **kwargs: Additional parameters (e.g., language, format)
            
        Returns:
            Prompt string for OCR task
        """
        language = kwargs.get('language', 'any language')
        preserve_formatting = kwargs.get('preserve_formatting', True)
        
        if model_type == ModelType.VLM:
            # Vision-Language Model (can see images directly)
            prompt = f"""Extract all text from this image.

Requirements:
- Extract text in {language}
- Maintain original text order (top to bottom, left to right)
{"- Preserve formatting, line breaks, and structure" if preserve_formatting else "- Return plain text without formatting"}
- Include all visible text, numbers, and symbols
- Do not add explanations or descriptions

Return only the extracted text."""
            
        elif model_type == ModelType.LLM:
            # Language Model (receives pre-processed text or base64)
            prompt = f"""You are an OCR text extraction assistant.

Extract and clean the text from the provided document.

Requirements:
- Maintain original text order
{"- Preserve formatting and structure" if preserve_formatting else "- Return clean plain text"}
- Fix obvious OCR errors if any
- Do not add explanations

Return only the extracted text."""
            
        else:  # ModelType.OCR
            # Dedicated OCR Model (minimal prompt needed)
            prompt = "Extract all text from this image."
        
        return prompt
    
    # =========================================================================
    # CLASSIFY TASK PROMPTS
    # =========================================================================
    
    @staticmethod
    def get_classify_prompt(
        model_type: ModelType,
        document_types: List[Dict[str, str]],
        text: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Get classification prompt for categorizing documents.
        
        Args:
            model_type: Type of model (VLM, LLM, OCR)
            document_types: List of dicts with 'doc_type' and 'description'
            text: Document text (for LLM models)
            **kwargs: Additional parameters
            
        Returns:
            Prompt string for classification task
        """
        # Build document types list
        types_list = "\n".join([
            f"- {dt['doc_type']}: {dt['description']}"
            for dt in document_types
        ])
        
        if model_type == ModelType.VLM:
            # Vision-Language Model (can see document directly)
            prompt = f"""Analyze this document image and classify it into one of the following types:

{types_list}

Examine the document's:
- Layout and structure
- Content and text
- Visual elements (logos, stamps, signatures)
- Formatting and style

Respond in JSON format:
{{
    "document_type": "the matching type",
    "confidence": 0.95,
    "reasoning": "brief explanation of why this classification"
}}

Respond ONLY with valid JSON."""
            
        elif model_type == ModelType.LLM:
            # Language Model (receives extracted text)
            text_preview = text[:3000] if text else "[text will be provided]"
            
            prompt = f"""Classify this document into one of the following types:

{types_list}

Document text:
{text_preview}

Analyze the content, terminology, and structure to determine the document type.

Respond in JSON format:
{{
    "document_type": "the matching type",
    "confidence": 0.95,
    "reasoning": "brief explanation"
}}

Respond ONLY with valid JSON."""
            
        else:  # ModelType.OCR
            # OCR models don't classify, return error message
            prompt = "ERROR: OCR models cannot perform classification. Use LLM or VLM models."
        
        return prompt
    
    # =========================================================================
    # EXTRACT TASK PROMPTS
    # =========================================================================
    
    @staticmethod
    def get_extract_prompt(
        model_type: ModelType,
        schema_fields: List[Dict[str, any]],
        text: Optional[str] = None,
        target: str = "document",
        **kwargs
    ) -> str:
        """
        Get extraction prompt for structured data extraction.
        
        Args:
            model_type: Type of model (VLM, LLM, OCR)
            schema_fields: List of field definitions with name, type, description, required
            text: Document text (for LLM models)
            target: Extraction target (document, page, table_row)
            **kwargs: Additional parameters
            
        Returns:
            Prompt string for extraction task
        """
        # Build schema description
        schema_desc = []
        for field in schema_fields:
            field_info = f"- {field['name']} ({field['type']})"
            if field.get('description'):
                field_info += f": {field['description']}"
            if field.get('required'):
                field_info += " [REQUIRED]"
            schema_desc.append(field_info)
        
        schema_text = "\n".join(schema_desc)
        
        # Target description
        target_desc = {
            "document": "Extract data from the entire document",
            "page": "Extract data from each page separately",
            "table_row": "Extract data from each table row"
        }.get(target, "Extract data")
        
        if model_type == ModelType.VLM:
            # Vision-Language Model (can see document directly)
            prompt = f"""{target_desc} according to this schema:

{schema_text}

Analyze the document image and extract the requested information.

Instructions:
- Look for the information in the document layout
- Extract exact values as they appear
- Use null for missing optional fields
- Ensure required fields are present

Return the extracted data as JSON. For required fields, ensure they are present. Use null for missing optional fields.

Respond ONLY with valid JSON."""
            
        elif model_type == ModelType.LLM:
            # Language Model (receives extracted text)
            text_content = text if text else "[text will be provided]"
            
            prompt = f"""{target_desc} according to this schema:

{schema_text}

Text to extract from:
---
{text_content}
---

Instructions:
- Extract information from the text above
- Match field types exactly
- Use null for missing optional fields
- Ensure required fields are present

Return the extracted data as JSON. For required fields, ensure they are present. Use null for missing optional fields.

Respond ONLY with valid JSON."""
            
        else:  # ModelType.OCR
            # OCR models don't extract structured data
            prompt = "ERROR: OCR models cannot perform structured extraction. Use LLM or VLM models."
        
        return prompt
    
    # =========================================================================
    # SPLIT TASK PROMPTS
    # =========================================================================
    
    @staticmethod
    def get_split_prompt(
        model_type: ModelType,
        categories: List[Dict[str, str]],
        allow_uncategorized: bool = True,
        **kwargs
    ) -> str:
        """
        Get splitting prompt for document chunking and categorization.
        
        Args:
            model_type: Type of model (VLM, LLM, OCR)
            categories: List of dicts with 'name' and 'description'
            allow_uncategorized: Whether to allow unknown category
            **kwargs: Additional parameters
            
        Returns:
            Prompt string for splitting task
        """
        # Build categories list
        categories_list = "\n".join([
            f"{i+1}. {cat['name']}: {cat['description']}"
            for i, cat in enumerate(categories)
        ])
        
        unknown_instruction = (
            'If content doesn\'t fit any category, mark it as "unknown".'
            if allow_uncategorized
            else 'All content must be assigned to one of the defined categories.'
        )
        
        if model_type == ModelType.VLM:
            # Vision-Language Model (can see document directly)
            prompt = f"""Analyze this document and split it into chunks based on these categories:

{categories_list}

For each section or chunk in the document, assign it to the most appropriate category.
{unknown_instruction}

Examine:
- Visual layout and structure
- Section headings and titles
- Content and context
- Page boundaries

Return results in JSON format:
{{
  "chunks": [
    {{
      "content": "text content here",
      "category": "category_name",
      "page_number": 1,
      "confidence": 0.95
    }}
  ]
}}

Important:
- Preserve original text exactly
- Maintain document order
- Include page numbers
- Provide confidence scores (0.0 to 1.0)
- Use exact category names or "unknown"

Respond ONLY with valid JSON."""
            
        elif model_type == ModelType.LLM:
            # Language Model (receives extracted text)
            prompt = f"""Split this document text into chunks based on these categories:

{categories_list}

For each section or chunk, assign it to the most appropriate category.
{unknown_instruction}

Analyze:
- Section headings and structure
- Content and context
- Topic changes
- Logical boundaries

Return results in JSON format:
{{
  "chunks": [
    {{
      "content": "text content here",
      "category": "category_name",
      "page_number": 1,
      "confidence": 0.95
    }}
  ]
}}

Important:
- Preserve original text exactly
- Maintain document order
- Provide confidence scores (0.0 to 1.0)
- Use exact category names or "unknown"

Respond ONLY with valid JSON."""
            
        else:  # ModelType.OCR
            # OCR models don't split documents
            prompt = "ERROR: OCR models cannot perform document splitting. Use LLM or VLM models."
        
        return prompt
    
    # =========================================================================
    # SYSTEM PROMPTS
    # =========================================================================
    
    @staticmethod
    def get_system_prompt(model_type: ModelType, task_type: TaskType) -> Optional[str]:
        """
        Get system prompt for a specific model type and task.
        
        Args:
            model_type: Type of model (VLM, LLM, OCR)
            task_type: Type of task (OCR, CLASSIFY, EXTRACT, SPLIT)
            
        Returns:
            System prompt string or None
        """
        system_prompts = {
            (ModelType.VLM, TaskType.OCR): "You are an expert OCR system with vision capabilities. Extract text accurately from images.",
            (ModelType.VLM, TaskType.CLASSIFY): "You are a document classification expert. Analyze document images and categorize them accurately.",
            (ModelType.VLM, TaskType.EXTRACT): "You are a data extraction specialist. Extract structured information from document images.",
            (ModelType.VLM, TaskType.SPLIT): "You are a document analysis expert. Split documents into logical, categorized sections.",
            
            (ModelType.LLM, TaskType.OCR): "You are an OCR text processing assistant. Clean and format extracted text.",
            (ModelType.LLM, TaskType.CLASSIFY): "You are a document classification expert. Categorize documents based on their content.",
            (ModelType.LLM, TaskType.EXTRACT): "You are a data extraction specialist. Extract structured information from text accurately.",
            (ModelType.LLM, TaskType.SPLIT): "You are a document analysis expert. Split text into logical, categorized sections.",
            
            (ModelType.OCR, TaskType.OCR): None,  # OCR models don't use system prompts
        }
        
        return system_prompts.get((model_type, task_type))
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    @staticmethod
    def detect_model_type(provider: str) -> ModelType:
        """
        Detect model type from provider name.
        
        Args:
            provider: Provider name (poe_api, google_studio, lmstudio, etc.)
            
        Returns:
            ModelType enum value
        """
        provider_lower = provider.lower()
        
        # VLM providers (vision-capable)
        if provider_lower in ['google_studio', 'google', 'poe_vision']:
            return ModelType.VLM
        
        # LLM providers (text-only)
        elif provider_lower in ['poe_api', 'poe', 'ollama']:
            return ModelType.LLM
        
        # OCR providers (dedicated OCR)
        elif provider_lower in ['lm_studio', 'lmstudio', 'vllm', 'lightonocr_api']:
            return ModelType.OCR
        
        # Default to LLM
        return ModelType.LLM
    
    @staticmethod
    def format_prompt_with_context(
        base_prompt: str,
        context: Optional[Dict[str, any]] = None
    ) -> str:
        """
        Format prompt with additional context.
        
        Args:
            base_prompt: Base prompt template
            context: Additional context to include
            
        Returns:
            Formatted prompt string
        """
        if not context:
            return base_prompt
        
        context_parts = []
        
        if context.get('language'):
            context_parts.append(f"Language: {context['language']}")
        
        if context.get('format'):
            context_parts.append(f"Output format: {context['format']}")
        
        if context.get('instructions'):
            context_parts.append(f"Additional instructions: {context['instructions']}")
        
        if context_parts:
            context_text = "\n".join(context_parts)
            return f"{base_prompt}\n\nContext:\n{context_text}"
        
        return base_prompt


# Convenience functions for quick access
def get_ocr_prompt(provider: str, **kwargs) -> str:
    """Get OCR prompt for a provider."""
    model_type = PromptTemplates.detect_model_type(provider)
    return PromptTemplates.get_ocr_prompt(model_type, **kwargs)


def get_classify_prompt(provider: str, document_types: List[Dict[str, str]], **kwargs) -> str:
    """Get classification prompt for a provider."""
    model_type = PromptTemplates.detect_model_type(provider)
    return PromptTemplates.get_classify_prompt(model_type, document_types, **kwargs)


def get_extract_prompt(provider: str, schema_fields: List[Dict[str, any]], **kwargs) -> str:
    """Get extraction prompt for a provider."""
    model_type = PromptTemplates.detect_model_type(provider)
    return PromptTemplates.get_extract_prompt(model_type, schema_fields, **kwargs)


def get_split_prompt(provider: str, categories: List[Dict[str, str]], **kwargs) -> str:
    """Get splitting prompt for a provider."""
    model_type = PromptTemplates.detect_model_type(provider)
    return PromptTemplates.get_split_prompt(model_type, categories, **kwargs)


def get_system_prompt(provider: str, task: str) -> Optional[str]:
    """Get system prompt for a provider and task."""
    model_type = PromptTemplates.detect_model_type(provider)
    task_type = TaskType(task.lower())
    return PromptTemplates.get_system_prompt(model_type, task_type)
