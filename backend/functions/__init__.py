"""
Backend functions for Dr.Vision document processing pipeline.

This module provides high-level functions that orchestrate agents and processors:
- Parser: File type detection and text extraction
- Text Parser: Markdown/HTML to plain text conversion
- Classifier: Document classification
- Schema Generator: Dynamic schema generation
- Extractor: Structured data extraction
- Splitter: Document chunking
"""

from functions.parser import Parser, ParseResult
from functions.text_parser import TextParser
from functions.classifier import Classifier, ClassifyResult, ClassificationRule
from functions.schema_generator import SchemaGenerator, GenerateSchemaResult
from functions.extractor import Extractor, ExtractResult
from functions.splitter import Splitter, SplitResult, ChunkCategory

__all__ = [
    'Parser',
    'ParseResult',
    'TextParser',
    'Classifier',
    'ClassifyResult',
    'ClassificationRule',
    'SchemaGenerator',
    'GenerateSchemaResult',
    'Extractor',
    'ExtractResult',
    'Splitter',
    'SplitResult',
    'ChunkCategory',
]
