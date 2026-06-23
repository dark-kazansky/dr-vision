"""
DeepDoc Vision Module.

Provides:
- LayoutRecognizer: Document layout detection (10 labels)
- TableStructureRecognizer: Table structure detection (6 labels)
- Recognizer: Base ONNX inference class
"""

from .recognizer import Recognizer
from .layout_recognizer import LayoutRecognizer
from .table_structure_recognizer import TableStructureRecognizer

__all__ = ["Recognizer", "LayoutRecognizer", "TableStructureRecognizer"]
