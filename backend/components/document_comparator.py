"""
Document Comparator — Compare two documents and produce a detailed diff analysis.

Provides:
- Word-level text diff (additions, deletions, modifications)
- Similarity score (0.0 = completely different, 1.0 = identical)
- Line-level diff with context
- Section/paragraph comparison
- Summary statistics

Uses Python's difflib for reliable sequence matching.
Does NOT perform OCR — expects pre-extracted text as input.
Typically chained after parse steps in the workflow pipeline.

Usage:
    from components.document_comparator import DocumentComparator

    comparator = DocumentComparator()
    result = comparator.compare(text_a, text_b)
    print(result.similarity_score)  # 0.87
    print(result.additions)         # ["new paragraph..."]
"""

import difflib
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class DiffChunk:
    """A single chunk of difference between two texts."""

    type: str  # "addition", "deletion", "modification", "equal"
    content: str
    line_start: int = 0
    line_end: int = 0
    # For modifications: the original text
    original: Optional[str] = None

    def to_dict(self) -> dict:
        d: Dict[str, Any] = {
            "type": self.type,
            "content": self.content,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }
        if self.original is not None:
            d["original"] = self.original
        return d


@dataclass
class CompareResult:
    """Result of document comparison."""

    success: bool
    similarity_score: float = 0.0  # 0.0 to 1.0
    is_identical: bool = False
    diff_chunks: List[DiffChunk] = field(default_factory=list)
    additions: List[str] = field(default_factory=list)
    deletions: List[str] = field(default_factory=list)
    modifications: List[Dict[str, str]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    unified_diff: str = ""
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "similarity_score": round(self.similarity_score, 4),
            "is_identical": self.is_identical,
            "diff_chunks": [c.to_dict() for c in self.diff_chunks],
            "additions": self.additions,
            "deletions": self.deletions,
            "modifications": self.modifications,
            "stats": self.stats,
            "unified_diff": self.unified_diff,
            "error": self.error,
        }


# =============================================================================
# Document Comparator
# =============================================================================


class DocumentComparator:
    """
    Compare two documents and produce a detailed diff analysis.

    Comparison modes:
    - Line-level: compare documents line by line (default)
    - Word-level: compare individual words (more granular)
    - Paragraph-level: compare logical paragraphs

    Usage:
        comparator = DocumentComparator()
        result = comparator.compare("text A", "text B")
    """

    def __init__(
        self,
        mode: str = "line",
        context_lines: int = 3,
        ignore_whitespace: bool = False,
        ignore_case: bool = False,
    ):
        """
        Args:
            mode: Comparison mode — "line", "word", or "paragraph"
            context_lines: Lines of context around changes in unified diff
            ignore_whitespace: Normalize whitespace before comparing
            ignore_case: Case-insensitive comparison
        """
        self.mode = mode
        self.context_lines = context_lines
        self.ignore_whitespace = ignore_whitespace
        self.ignore_case = ignore_case

    def compare(self, text_a: str, text_b: str) -> CompareResult:
        """
        Compare two text documents.

        Args:
            text_a: First document text (the "original")
            text_b: Second document text (the "modified")

        Returns:
            CompareResult with similarity score, diffs, and statistics
        """
        if text_a is None:
            text_a = ""
        if text_b is None:
            text_b = ""

        try:
            # Normalize if configured
            norm_a = self._normalize(text_a)
            norm_b = self._normalize(text_b)

            # Check identity
            if norm_a == norm_b:
                return CompareResult(
                    success=True,
                    similarity_score=1.0,
                    is_identical=True,
                    stats=self._compute_stats(text_a, text_b, [], [], []),
                )

            # Compute similarity using SequenceMatcher
            similarity = self._compute_similarity(norm_a, norm_b)

            # Generate diffs based on mode
            if self.mode == "word":
                diff_chunks, additions, deletions, modifications = self._word_diff(norm_a, norm_b)
            elif self.mode == "paragraph":
                diff_chunks, additions, deletions, modifications = self._paragraph_diff(norm_a, norm_b)
            else:
                diff_chunks, additions, deletions, modifications = self._line_diff(norm_a, norm_b)

            # Generate unified diff
            unified = self._unified_diff(norm_a, norm_b)

            # Compute stats
            stats = self._compute_stats(text_a, text_b, additions, deletions, modifications)

            return CompareResult(
                success=True,
                similarity_score=similarity,
                is_identical=False,
                diff_chunks=diff_chunks,
                additions=additions,
                deletions=deletions,
                modifications=modifications,
                stats=stats,
                unified_diff=unified,
            )

        except Exception as e:
            logger.warning("Document comparison failed: %s", e)
            return CompareResult(success=False, error=str(e))

    def compare_files(self, file_path_a: str, file_path_b: str) -> CompareResult:
        """
        Compare two files by reading their content.

        For non-text files (PDF, images), this requires prior OCR/parsing.
        This method only handles text files directly.
        """
        try:
            with open(file_path_a, "r", encoding="utf-8") as f:
                text_a = f.read()
        except UnicodeDecodeError:
            return CompareResult(
                success=False,
                error=f"Cannot read file A as text: {file_path_a}. Run OCR first.",
            )
        except FileNotFoundError:
            return CompareResult(success=False, error=f"File not found: {file_path_a}")

        try:
            with open(file_path_b, "r", encoding="utf-8") as f:
                text_b = f.read()
        except UnicodeDecodeError:
            return CompareResult(
                success=False,
                error=f"Cannot read file B as text: {file_path_b}. Run OCR first.",
            )
        except FileNotFoundError:
            return CompareResult(success=False, error=f"File not found: {file_path_b}")

        return self.compare(text_a, text_b)

    # ------------------------------------------------------------------
    # Diff algorithms
    # ------------------------------------------------------------------

    def _line_diff(self, text_a: str, text_b: str):
        """Line-by-line diff."""
        lines_a = text_a.splitlines()
        lines_b = text_b.splitlines()

        diff_chunks: List[DiffChunk] = []
        additions: List[str] = []
        deletions: List[str] = []
        modifications: List[Dict[str, str]] = []

        matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
        line_num = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                line_num += (i2 - i1)
            elif tag == "insert":
                content = "\n".join(lines_b[j1:j2])
                diff_chunks.append(DiffChunk(
                    type="addition", content=content, line_start=line_num, line_end=line_num,
                ))
                additions.append(content)
            elif tag == "delete":
                content = "\n".join(lines_a[i1:i2])
                diff_chunks.append(DiffChunk(
                    type="deletion", content=content, line_start=line_num, line_end=line_num + (i2 - i1),
                ))
                deletions.append(content)
                line_num += (i2 - i1)
            elif tag == "replace":
                original = "\n".join(lines_a[i1:i2])
                modified = "\n".join(lines_b[j1:j2])
                diff_chunks.append(DiffChunk(
                    type="modification", content=modified, original=original,
                    line_start=line_num, line_end=line_num + (i2 - i1),
                ))
                modifications.append({"original": original, "modified": modified})
                line_num += (i2 - i1)

        return diff_chunks, additions, deletions, modifications

    def _word_diff(self, text_a: str, text_b: str):
        """Word-level diff (more granular)."""
        words_a = text_a.split()
        words_b = text_b.split()

        diff_chunks: List[DiffChunk] = []
        additions: List[str] = []
        deletions: List[str] = []
        modifications: List[Dict[str, str]] = []

        matcher = difflib.SequenceMatcher(None, words_a, words_b)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            elif tag == "insert":
                content = " ".join(words_b[j1:j2])
                diff_chunks.append(DiffChunk(type="addition", content=content))
                additions.append(content)
            elif tag == "delete":
                content = " ".join(words_a[i1:i2])
                diff_chunks.append(DiffChunk(type="deletion", content=content))
                deletions.append(content)
            elif tag == "replace":
                original = " ".join(words_a[i1:i2])
                modified = " ".join(words_b[j1:j2])
                diff_chunks.append(DiffChunk(type="modification", content=modified, original=original))
                modifications.append({"original": original, "modified": modified})

        return diff_chunks, additions, deletions, modifications

    def _paragraph_diff(self, text_a: str, text_b: str):
        """Paragraph-level diff (split on double newlines)."""
        paras_a = re.split(r"\n\s*\n", text_a.strip())
        paras_b = re.split(r"\n\s*\n", text_b.strip())

        diff_chunks: List[DiffChunk] = []
        additions: List[str] = []
        deletions: List[str] = []
        modifications: List[Dict[str, str]] = []

        matcher = difflib.SequenceMatcher(None, paras_a, paras_b)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            elif tag == "insert":
                for p in paras_b[j1:j2]:
                    diff_chunks.append(DiffChunk(type="addition", content=p))
                    additions.append(p)
            elif tag == "delete":
                for p in paras_a[i1:i2]:
                    diff_chunks.append(DiffChunk(type="deletion", content=p))
                    deletions.append(p)
            elif tag == "replace":
                for idx in range(max(i2 - i1, j2 - j1)):
                    orig = paras_a[i1 + idx] if (i1 + idx) < i2 else ""
                    mod = paras_b[j1 + idx] if (j1 + idx) < j2 else ""
                    if orig and mod:
                        diff_chunks.append(DiffChunk(type="modification", content=mod, original=orig))
                        modifications.append({"original": orig, "modified": mod})
                    elif mod:
                        diff_chunks.append(DiffChunk(type="addition", content=mod))
                        additions.append(mod)
                    elif orig:
                        diff_chunks.append(DiffChunk(type="deletion", content=orig))
                        deletions.append(orig)

        return diff_chunks, additions, deletions, modifications

    # ------------------------------------------------------------------
    # Similarity scoring
    # ------------------------------------------------------------------

    def _compute_similarity(self, text_a: str, text_b: str) -> float:
        """Compute similarity ratio using SequenceMatcher."""
        if not text_a and not text_b:
            return 1.0
        if not text_a or not text_b:
            return 0.0

        # For very long texts, use a sample for performance
        max_len = 50000
        if len(text_a) > max_len or len(text_b) > max_len:
            # Use word-level comparison for long texts
            words_a = text_a[:max_len].split()
            words_b = text_b[:max_len].split()
            return difflib.SequenceMatcher(None, words_a, words_b).ratio()

        return difflib.SequenceMatcher(None, text_a, text_b).ratio()

    # ------------------------------------------------------------------
    # Unified diff
    # ------------------------------------------------------------------

    def _unified_diff(self, text_a: str, text_b: str) -> str:
        """Generate unified diff format."""
        lines_a = text_a.splitlines(keepends=True)
        lines_b = text_b.splitlines(keepends=True)

        diff_lines = difflib.unified_diff(
            lines_a, lines_b,
            fromfile="document_a",
            tofile="document_b",
            n=self.context_lines,
        )
        return "".join(diff_lines)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def _compute_stats(
        self,
        text_a: str,
        text_b: str,
        additions: List[str],
        deletions: List[str],
        modifications: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Compute comparison statistics."""
        words_a = len(text_a.split()) if text_a else 0
        words_b = len(text_b.split()) if text_b else 0
        lines_a = text_a.count("\n") + 1 if text_a else 0
        lines_b = text_b.count("\n") + 1 if text_b else 0

        added_words = sum(len(a.split()) for a in additions)
        deleted_words = sum(len(d.split()) for d in deletions)
        modified_count = len(modifications)

        return {
            "document_a": {"words": words_a, "lines": lines_a, "chars": len(text_a)},
            "document_b": {"words": words_b, "lines": lines_b, "chars": len(text_b)},
            "additions_count": len(additions),
            "deletions_count": len(deletions),
            "modifications_count": modified_count,
            "total_changes": len(additions) + len(deletions) + modified_count,
            "added_words": added_words,
            "deleted_words": deleted_words,
            "word_count_diff": words_b - words_a,
        }

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    def _normalize(self, text: str) -> str:
        """Normalize text based on configuration."""
        if self.ignore_case:
            text = text.lower()
        if self.ignore_whitespace:
            # Collapse whitespace but preserve newlines
            lines = text.splitlines()
            lines = [re.sub(r"[ \t]+", " ", line).strip() for line in lines]
            text = "\n".join(lines)
        return text
