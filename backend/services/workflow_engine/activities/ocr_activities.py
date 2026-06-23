"""
OCR Activities — Wraps existing OCR operations as durable workflow activities.

Each activity:
1. Extracts parameters from the task payload
2. Calls the existing business logic (parser, classifier, extractor, splitter)
3. Returns structured output

These are thin wrappers — all heavy lifting is done by the existing components.
The workflow engine handles retry, timeout, and state management.
"""

import asyncio
import logging
from typing import Any, Dict

from services.workflow_engine.activities.base import (
    ActivityContext,
    ActivityError,
    NonRetryableError,
)
from services.workflow_engine.models import ActivityTask

logger = logging.getLogger(__name__)


async def handle_ocr_parse(task: ActivityTask) -> Dict[str, Any]:
    """
    OCR Parse activity — Extract text from a document.

    Input (from task.payload):
        - workflow_input.file_path: Path to the file to parse
        - config.tier: Processing tier (Normal/Premium)

    Output:
        - text: Extracted text content
        - file_type: Detected file type
        - pages: Number of pages processed
    """
    ctx = ActivityContext(task.payload)
    file_path = ctx.file_path
    tier = ctx.tier

    if not file_path:
        raise NonRetryableError("No file_path provided in workflow input")

    try:
        from agents.factory import AgentFactory
        from components.parser import Parser
        from config import Config, TierConfig

        config = Config.load()
        model_id = TierConfig.get_parser_model(tier)
        ocr_agent = AgentFactory.create_from_config(config, model_id)
        parser = Parser(ocr_agent=ocr_agent)

        result = await asyncio.to_thread(parser.parse, file_path)

        if not result.success:
            raise ActivityError(f"Parse failed: {result.error}")

        return {
            "text": result.text,
            "file_type": result.file_type,
            "pages": result.pages,
        }

    except (ActivityError, NonRetryableError):
        raise
    except ImportError as e:
        raise NonRetryableError(f"Missing dependency: {e}")
    except FileNotFoundError:
        raise NonRetryableError(f"File not found: {file_path}")
    except Exception as e:
        raise ActivityError(f"Parse error: {e}")


async def handle_ocr_classify(task: ActivityTask) -> Dict[str, Any]:
    """
    OCR Classify activity — Classify a document by type.

    Input:
        - workflow_input.file_path: Path to the file
        - config.tier: Processing tier
        - config.rules: Classification rules [{doc_type, description}]
        - previous_output.text: (optional) Pre-parsed text to classify

    Output:
        - document_type: Detected document type
        - confidence: Classification confidence score
        - reasoning: Explanation of classification
    """
    ctx = ActivityContext(task.payload)
    file_path = ctx.file_path
    tier = ctx.tier
    step_config = ctx.config

    if not file_path:
        raise NonRetryableError("No file_path provided in workflow input")

    try:
        from agents.factory import AgentFactory
        from components.classifier import Classifier, ClassificationRule
        from components.parser import Parser
        from config import Config, TierConfig

        config = Config.load()

        # Check if we have pre-parsed text from upstream
        text = None
        if ctx.previous_output and isinstance(ctx.previous_output, dict):
            text = ctx.previous_output.get("text")

        # If no upstream text, parse first
        if not text:
            parser_model_id = TierConfig.get_parser_model(tier)
            ocr_agent = AgentFactory.create_from_config(config, parser_model_id)
            parser = Parser(ocr_agent=ocr_agent)
            parse_result = await asyncio.to_thread(parser.parse, file_path)
            if not parse_result.success:
                raise ActivityError(f"Parse failed during classify: {parse_result.error}")
            text = parse_result.text

        # Classify
        classifier_model_id = TierConfig.get_classifier_llm_model(tier)
        llm_agent = AgentFactory.create_llm_agent(classifier_model_id, config=config)
        classifier = Classifier(agent=llm_agent)

        rules = [
            ClassificationRule(doc_type=rule["doc_type"], description=rule["description"])
            for rule in step_config.get("rules", [])
        ]

        classify_result = await asyncio.to_thread(classifier.classify, text, rules)

        if not classify_result.success:
            raise ActivityError(f"Classify failed: {classify_result.error}")

        return {
            "document_type": classify_result.document_type,
            "confidence": classify_result.confidence,
            "reasoning": classify_result.reasoning,
        }

    except (ActivityError, NonRetryableError):
        raise
    except ImportError as e:
        raise NonRetryableError(f"Missing dependency: {e}")
    except Exception as e:
        raise ActivityError(f"Classify error: {e}")


async def handle_ocr_extract(task: ActivityTask) -> Dict[str, Any]:
    """
    OCR Extract activity — Extract structured data from a document.

    Input:
        - workflow_input.file_path: Path to the file
        - config.tier: Processing tier
        - config.schema: Extraction schema [{field_name, field_type, description}]
        - previous_output.text: (optional) Pre-parsed text

    Output:
        - fields: Dict of extracted field values
        - raw_response: Raw LLM response
    """
    ctx = ActivityContext(task.payload)
    file_path = ctx.file_path
    tier = ctx.tier
    step_config = ctx.config

    if not file_path:
        raise NonRetryableError("No file_path provided in workflow input")

    try:
        from agents.factory import AgentFactory
        from components.extractor import Extractor
        from components.parser import Parser
        from config import Config, TierConfig
        from core.schemas import ExtractionConfig, ExtractionTarget, FieldType, SchemaField

        config = Config.load()

        # Check for upstream text
        text = None
        if ctx.previous_output and isinstance(ctx.previous_output, dict):
            text = ctx.previous_output.get("text")

        # Parse if needed
        if not text:
            parser_model_id = TierConfig.get_parser_model(tier)
            ocr_agent = AgentFactory.create_from_config(config, parser_model_id)
            parser = Parser(ocr_agent=ocr_agent)
            parse_result = await asyncio.to_thread(parser.parse, file_path)
            if not parse_result.success:
                raise ActivityError(f"Parse failed during extract: {parse_result.error}")
            text = parse_result.text

        # Build extraction schema
        schema_fields = []
        for field_def in step_config.get("schema", []):
            field_type = FieldType(field_def.get("field_type", "text"))
            schema_fields.append(SchemaField(
                field_name=field_def["field_name"],
                field_type=field_type,
                description=field_def.get("description", ""),
            ))

        if not schema_fields:
            raise NonRetryableError("No extraction schema provided in config")

        extraction_config = ExtractionConfig(
            target=ExtractionTarget.DOCUMENT,
            schema=schema_fields,
        )

        # Extract
        extractor_model_id = TierConfig.get_extractor_llm_model(tier)
        llm_agent = AgentFactory.create_llm_agent(extractor_model_id, config=config)
        extractor = Extractor(agent=llm_agent)

        extract_result = await asyncio.to_thread(
            extractor.extract, text, extraction_config
        )

        if not extract_result.success:
            raise ActivityError(f"Extract failed: {extract_result.error}")

        return {
            "fields": extract_result.fields,
            "raw_response": extract_result.raw_response,
        }

    except (ActivityError, NonRetryableError):
        raise
    except ImportError as e:
        raise NonRetryableError(f"Missing dependency: {e}")
    except Exception as e:
        raise ActivityError(f"Extract error: {e}")


async def handle_ocr_split(task: ActivityTask) -> Dict[str, Any]:
    """
    OCR Split activity — Split a document into sections.

    Input:
        - workflow_input.file_path: Path to the file
        - config.tier: Processing tier
        - config.categories: Split categories [{name, description}]
        - previous_output.text: (optional) Pre-parsed text

    Output:
        - chunks: List of document chunks with category assignments
    """
    ctx = ActivityContext(task.payload)
    file_path = ctx.file_path
    tier = ctx.tier
    step_config = ctx.config

    if not file_path:
        raise NonRetryableError("No file_path provided in workflow input")

    try:
        from agents.factory import AgentFactory
        from components.parser import Parser
        from components.splitter import ChunkCategory, Splitter
        from config import Config, TierConfig

        config = Config.load()

        # Check for upstream text
        text = None
        if ctx.previous_output and isinstance(ctx.previous_output, dict):
            text = ctx.previous_output.get("text")

        # Parse if needed
        if not text:
            parser_model_id = TierConfig.get_parser_model(tier)
            ocr_agent = AgentFactory.create_from_config(config, parser_model_id)
            parser = Parser(ocr_agent=ocr_agent)
            parse_result = await asyncio.to_thread(parser.parse, file_path)
            if not parse_result.success:
                raise ActivityError(f"Parse failed during split: {parse_result.error}")
            text = parse_result.text

        # Build categories
        categories = [
            ChunkCategory(name=cat["name"], description=cat.get("description", ""))
            for cat in step_config.get("categories", [])
        ]

        # Split
        splitter_model_id = TierConfig.get_splitter_llm_model(tier)
        llm_agent = AgentFactory.create_llm_agent(splitter_model_id, config=config)
        splitter = Splitter(agent=llm_agent)

        split_result = await asyncio.to_thread(
            splitter.split, text, categories
        )

        if not split_result.success:
            raise ActivityError(f"Split failed: {split_result.error}")

        return {
            "chunks": [
                {
                    "text": chunk.text,
                    "category": chunk.category,
                    "confidence": chunk.confidence,
                }
                for chunk in split_result.chunks
            ],
        }

    except (ActivityError, NonRetryableError):
        raise
    except ImportError as e:
        raise NonRetryableError(f"Missing dependency: {e}")
    except Exception as e:
        raise ActivityError(f"Split error: {e}")


async def handle_ocr_layout_recognize(task: ActivityTask) -> Dict[str, Any]:
    """
    OCR Layout Recognize activity — Detect document layout structure.

    Input:
        - workflow_input.file_path: Path to the file
        - config.tier: Processing tier

    Output:
        - layouts: List of detected layout regions with types and bounding boxes
    """
    ctx = ActivityContext(task.payload)
    file_path = ctx.file_path
    tier = ctx.tier

    if not file_path:
        raise NonRetryableError("No file_path provided in workflow input")

    try:
        from agents.factory import AgentFactory
        from components.parser import Parser
        from config import Config, TierConfig

        config = Config.load()
        model_id = TierConfig.get_parser_model(tier)
        ocr_agent = AgentFactory.create_from_config(config, model_id)
        parser = Parser(ocr_agent=ocr_agent)

        # Layout recognition uses the same parser but with layout mode
        result = await asyncio.to_thread(parser.parse, file_path)

        if not result.success:
            raise ActivityError(f"Layout recognition failed: {result.error}")

        return {
            "text": result.text,
            "file_type": result.file_type,
            "pages": result.pages,
            "layout_mode": True,
        }

    except (ActivityError, NonRetryableError):
        raise
    except ImportError as e:
        raise NonRetryableError(f"Missing dependency: {e}")
    except Exception as e:
        raise ActivityError(f"Layout recognition error: {e}")


async def handle_table_recognize(task: ActivityTask) -> Dict[str, Any]:
    """
    Table Structure Recognition activity — Detect rows/columns/cells in tables.

    Input:
        - workflow_input.file_path: Path to the file
        - config.threshold: Confidence threshold (default 0.3)
        - config.scale_factor: PDF rendering scale (default 3)
        - config.output_format: json, csv, markdown, html, all (default json)
        - config.use_layout_detection: Whether to find tables via layout first (default True)

    Output:
        - tables: List of detected tables with cells
        - table_count: Number of tables found
        - csv/markdown/html: Formatted output (if requested)
    """
    ctx = ActivityContext(task.payload)
    file_path = ctx.file_path
    step_config = ctx.config

    if not file_path:
        raise NonRetryableError("No file_path provided in workflow input")

    try:
        from components.table_recognizer import TableRecognizeComponent

        threshold = step_config.get("threshold", 0.3)
        scale_factor = step_config.get("scale_factor", 3)
        output_format = step_config.get("output_format", "json")
        use_layout_detection = step_config.get("use_layout_detection", True)

        component = TableRecognizeComponent(
            threshold=threshold,
            scale_factor=scale_factor,
            use_layout_detection=use_layout_detection,
        )

        result = await asyncio.to_thread(component.recognize, file_path)

        if not result.success:
            raise ActivityError(f"Table recognition failed: {result.error}")

        output = result.to_dict()

        # Add formatted output based on config
        if output_format in ("csv", "all"):
            output["csv"] = [t.to_csv() for t in result.tables]
        if output_format in ("markdown", "all"):
            output["markdown"] = [t.to_markdown() for t in result.tables]
        if output_format in ("html", "all"):
            output["html"] = [t.to_html() for t in result.tables]

        return output

    except (ActivityError, NonRetryableError):
        raise
    except ImportError as e:
        raise NonRetryableError(f"Missing dependency: {e}")
    except FileNotFoundError:
        raise NonRetryableError(f"File not found: {file_path}")
    except Exception as e:
        raise ActivityError(f"Table recognition error: {e}")


async def handle_document_to_markdown(task: ActivityTask) -> Dict[str, Any]:
    """
    Document to Markdown activity — Convert documents preserving table structure.

    Uses Microsoft MarkItDown library for high-fidelity conversion.
    Best for: XLSX, DOCX, CSV, HTML, text-based PDF.

    Input:
        - workflow_input.file_path: Path to the document

    Output:
        - markdown: Full markdown text with preserved structure
        - tables: List of extracted markdown tables
        - source_format: Original file format
        - has_tables: Whether tables were found
    """
    ctx = ActivityContext(task.payload)
    file_path = ctx.file_path

    if not file_path:
        raise NonRetryableError("No file_path provided in workflow input")

    try:
        from components.markdown_converter import MarkdownConverter, extract_markdown_tables

        converter = MarkdownConverter()
        result = await asyncio.to_thread(converter.convert, file_path)

        if not result.success:
            raise ActivityError(f"Markdown conversion failed: {result.error}")

        output = result.to_dict()
        output["tables"] = extract_markdown_tables(result.markdown)
        return output

    except (ActivityError, NonRetryableError):
        raise
    except ImportError as e:
        raise NonRetryableError(f"Missing dependency: {e}")
    except FileNotFoundError:
        raise NonRetryableError(f"File not found: {file_path}")
    except Exception as e:
        raise ActivityError(f"Document to markdown error: {e}")


async def handle_ocr_postprocess(task: ActivityTask) -> Dict[str, Any]:
    """
    OCR Post-processing activity — Correct and score OCR text.

    Input:
        - previous_output.text: Raw OCR text from upstream parse node
        - config.language: Language (vi/en, default vi)
        - config.confidence_threshold: Threshold for flagging (default 0.7)

    Output:
        - processed_text: Corrected text
        - word_confidences: Per-word confidence scores
        - corrections: List of corrections applied
        - stats: Summary statistics
    """
    ctx = ActivityContext(task.payload)
    step_config = ctx.config

    # Get text from upstream or config
    text = ""
    if ctx.previous_output and isinstance(ctx.previous_output, dict):
        text = ctx.previous_output.get("text", "")
    if not text:
        text = step_config.get("text", "")

    if not text:
        return {"success": True, "processed_text": "", "corrections": [], "stats": {"word_count": 0}}

    try:
        from components.ocr_postprocessor import OCRPostProcessor

        language = step_config.get("language", "vi")
        threshold = step_config.get("confidence_threshold", 0.7)

        processor = OCRPostProcessor(
            language=language,
            confidence_threshold=threshold,
        )
        result = processor.process(text)

        if not result.success:
            raise ActivityError(f"OCR post-processing failed: {result.error}")

        return result.to_dict()

    except (ActivityError, NonRetryableError):
        raise
    except Exception as e:
        raise ActivityError(f"OCR post-processing error: {e}")


async def handle_template_extract(task: ActivityTask) -> Dict[str, Any]:
    """
    Template-based extraction activity.

    Auto-detects document type → matches template → extracts fields.

    Input:
        - workflow_input.file_path: Path to the document
        - config.template_id: (optional) Direct template ID to use
        - previous_output.text: (optional) Pre-parsed text for matching

    Output:
        - template_id, template_name, document_type
        - extracted_fields: Dict of field values
        - match_info: How the template was matched
    """
    ctx = ActivityContext(task.payload)
    file_path = ctx.file_path
    step_config = ctx.config

    if not file_path:
        raise NonRetryableError("No file_path provided in workflow input")

    try:
        from config import Config
        from services.workflow_service import _run_template_extract_step

        config = Config.load()
        tier = step_config.get("tier", "Normal")

        result = await _run_template_extract_step(file_path, tier, step_config, config)

        if not result.get("success"):
            raise ActivityError(f"Template extraction failed: {result.get('error', 'Unknown')}")

        return result

    except (ActivityError, NonRetryableError):
        raise
    except ImportError as e:
        raise NonRetryableError(f"Missing dependency: {e}")
    except Exception as e:
        raise ActivityError(f"Template extraction error: {e}")
