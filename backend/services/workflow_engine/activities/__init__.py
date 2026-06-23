"""
Activities — Concrete implementations of workflow activities.

Each activity wraps existing business logic (OCR, parse, classify, extract, split)
as a durable activity that can be executed by workers.

Activities are:
- Idempotent: Same input → same output (safe to retry)
- Stateless: All context comes from the task payload
- Self-contained: Each activity handles its own I/O

Registration:
    from services.workflow_engine.activities import get_all_handlers
    worker.register_handlers(get_all_handlers())
"""

from services.workflow_engine.activities.ocr_activities import (
    handle_ocr_classify,
    handle_ocr_extract,
    handle_ocr_layout_recognize,
    handle_ocr_parse,
    handle_ocr_split,
    handle_table_recognize,
    handle_document_to_markdown,
    handle_ocr_postprocess,
    handle_template_extract,
)
from services.workflow_engine.activities.base import ActivityError, ActivityContext

# All available activity handlers (activity_type → handler function)
_ALL_HANDLERS = {
    "ocr_parse": handle_ocr_parse,
    "ocr_classify": handle_ocr_classify,
    "ocr_extract": handle_ocr_extract,
    "ocr_split": handle_ocr_split,
    "ocr_layout_recognize": handle_ocr_layout_recognize,
    "table_recognize": handle_table_recognize,
    "document_to_markdown": handle_document_to_markdown,
    "ocr_postprocess": handle_ocr_postprocess,
    "template_extract": handle_template_extract,
    # Legacy type aliases (backward compatibility with existing workflow definitions)
    "parse": handle_ocr_parse,
    "classify": handle_ocr_classify,
    "extract": handle_ocr_extract,
    "split": handle_ocr_split,
    "layout_recognize": handle_ocr_layout_recognize,
}


def get_all_handlers() -> dict:
    """Get all registered activity handlers."""
    return dict(_ALL_HANDLERS)


def get_handler(activity_type: str):
    """Get a specific activity handler by type."""
    return _ALL_HANDLERS.get(activity_type)


__all__ = [
    "get_all_handlers",
    "get_handler",
    "ActivityError",
    "ActivityContext",
    "handle_ocr_parse",
    "handle_ocr_classify",
    "handle_ocr_extract",
    "handle_ocr_split",
    "handle_ocr_layout_recognize",
    "handle_table_recognize",
    "handle_document_to_markdown",
]
