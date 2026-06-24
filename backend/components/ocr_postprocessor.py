"""
OCR Post-Processor — Auto-correction, confidence scoring, and text normalization.

Provides a configurable pipeline that improves raw OCR output:
1. Text normalization (whitespace, line breaks, unicode)
2. Common OCR error correction (l→1, O→0 in numbers, diacritics)
3. Per-word confidence scoring (heuristic-based)
4. Low-confidence word flagging

Designed for Vietnamese + English documents. Pattern-based (no ML model needed).

Usage:
    from components.ocr_postprocessor import OCRPostProcessor

    processor = OCRPostProcessor()
    result = processor.process("1OO.OOO VND", language="vi")
    print(result.processed_text)   # "100.000 VND"
    print(result.corrections)      # [{"original": "1OO.OOO", "corrected": "100.000", ...}]
"""

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class WordConfidence:
    """Confidence information for a single word."""

    text: str
    confidence: float  # 0.0 - 1.0
    is_corrected: bool = False
    original: Optional[str] = None
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d: Dict[str, Any] = {
            "text": self.text,
            "confidence": round(self.confidence, 3),
        }
        if self.is_corrected:
            d["is_corrected"] = True
            d["original"] = self.original
        if self.flags:
            d["flags"] = self.flags
        return d


@dataclass
class Correction:
    """A single correction applied to the text."""

    original: str
    corrected: str
    rule: str
    position: int = 0  # character offset in original text

    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "corrected": self.corrected,
            "rule": self.rule,
            "position": self.position,
        }


@dataclass
class PostProcessResult:
    """Result of OCR post-processing."""

    success: bool
    processed_text: str = ""
    original_text: str = ""
    word_confidences: List[WordConfidence] = field(default_factory=list)
    corrections: List[Correction] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "processed_text": self.processed_text,
            "original_text": self.original_text,
            "word_confidences": [w.to_dict() for w in self.word_confidences],
            "corrections": [c.to_dict() for c in self.corrections],
            "stats": self.stats,
            "error": self.error,
        }


# =============================================================================
# Correction Rules
# =============================================================================

# Common OCR letter-to-digit confusion patterns (context: numeric strings)
_LETTER_DIGIT_MAP = {
    "O": "0", "o": "0",
    "l": "1", "I": "1", "|": "1",
    "S": "5", "s": "5",
    "B": "8",
    "Z": "2", "z": "2",
    "G": "6",
    "b": "6",
    "q": "9",
    "D": "0",
}

# Common Vietnamese diacritics OCR errors
_VIETNAMESE_CORRECTIONS = [
    # Missing/wrong diacritics on common words
    (r"\bđuợc\b", "được"),
    (r"\bnguời\b", "người"),
    (r"\bcủa\b", "của"),  # already correct but catches cua → của in context
    (r"\bkhông\b", "không"),
    (r"\bnhũng\b", "những"),
    (r"\btrưòng\b", "trường"),
    (r"\bthuong\b", "thương"),
    (r"\bnguoi\b", "người"),
    (r"\bcong ty\b", "công ty"),
    (r"\bso\b(?=\s*[\d:])", "số"),  # "so 123" → "số 123"
    (r"\bngay\b(?=\s*\d)", "ngày"),  # "ngay 01/01" → "ngày 01/01"
    (r"\bnam\b(?=\s*\d{4})", "năm"),  # "nam 2024" → "năm 2024"
]

# Number format corrections (Vietnamese/international)
_NUMBER_PATTERNS = [
    # Fix O/o in numbers: "1OO.OOO" → "100.000"
    (r"(?<=\d)[Oo]", "0"),
    # Fix l/I in numbers: "1l0" → "110"
    (r"(?<=\d)[lI|](?=\d)", "1"),
    # Fix S in numbers: "1S0" → "150"
    (r"(?<=\d)[Ss](?=\d)", "5"),
]

# Currency and unit patterns
_CURRENCY_PATTERNS = [
    (r"(?i)\bvnđ\b", "VNĐ"),
    (r"(?i)\bvnd\b", "VND"),
    (r"(?i)\busd\b", "USD"),
    (r"(?i)\beur\b", "EUR"),
]

# Whitespace normalization
_WHITESPACE_PATTERNS = [
    (r"[ \t]+", " "),  # Multiple spaces → single
    (r"\n{3,}", "\n\n"),  # Multiple newlines → double
    (r"^\s+", ""),  # Leading whitespace per line
    (r"\s+$", ""),  # Trailing whitespace per line
]


# =============================================================================
# OCR Post-Processor
# =============================================================================


class OCRPostProcessor:
    """
    Configurable OCR post-processing pipeline.

    Pipeline stages (in order):
    1. Unicode normalization (NFC)
    2. Whitespace cleanup
    3. Number correction (letter → digit in numeric contexts)
    4. Vietnamese diacritics correction
    5. Currency/unit normalization
    6. Per-word confidence scoring
    7. Low-confidence flagging
    """

    def __init__(
        self,
        language: str = "vi",
        confidence_threshold: float = 0.7,
        enable_number_correction: bool = True,
        enable_diacritics_correction: bool = True,
        enable_currency_normalization: bool = True,
        custom_rules: Optional[List[Tuple[str, str]]] = None,
    ):
        """
        Args:
            language: Primary language ("vi" for Vietnamese, "en" for English)
            confidence_threshold: Words below this threshold are flagged
            enable_number_correction: Fix letter-digit confusion in numbers
            enable_diacritics_correction: Fix Vietnamese diacritics errors
            enable_currency_normalization: Normalize currency/unit strings
            custom_rules: Additional (pattern, replacement) rules
        """
        self.language = language
        self.confidence_threshold = confidence_threshold
        self.enable_number_correction = enable_number_correction
        self.enable_diacritics_correction = enable_diacritics_correction
        self.enable_currency_normalization = enable_currency_normalization
        self.custom_rules = custom_rules or []

    def process(self, text: str) -> PostProcessResult:
        """
        Run the full post-processing pipeline on OCR text.

        Args:
            text: Raw OCR output text

        Returns:
            PostProcessResult with corrected text, confidences, and corrections
        """
        if not text or not text.strip():
            return PostProcessResult(
                success=True,
                processed_text="",
                original_text=text or "",
                stats={"word_count": 0, "correction_count": 0},
            )

        try:
            original_text = text
            corrections: List[Correction] = []

            # Stage 1: Unicode normalization
            text = unicodedata.normalize("NFC", text)

            # Stage 2: Whitespace cleanup
            text = self._normalize_whitespace(text)

            # Stage 3: Number correction
            if self.enable_number_correction:
                text, num_corrections = self._correct_numbers(text)
                corrections.extend(num_corrections)

            # Stage 4: Vietnamese diacritics
            if self.enable_diacritics_correction and self.language == "vi":
                text, vn_corrections = self._correct_vietnamese(text)
                corrections.extend(vn_corrections)

            # Stage 5: Currency normalization
            if self.enable_currency_normalization:
                text, cur_corrections = self._normalize_currency(text)
                corrections.extend(cur_corrections)

            # Stage 6: Custom rules
            for pattern, replacement in self.custom_rules:
                matches = list(re.finditer(pattern, text))
                if matches:
                    for m in reversed(matches):
                        original_match = m.group()
                        if original_match != replacement:
                            corrections.append(Correction(
                                original=original_match,
                                corrected=replacement,
                                rule="custom",
                                position=m.start(),
                            ))
                    text = re.sub(pattern, replacement, text)

            # Stage 7: Per-word confidence scoring
            word_confidences = self._score_words(text, original_text, corrections)

            # Stats
            total_words = len(word_confidences)
            low_confidence_count = sum(
                1 for w in word_confidences
                if w.confidence < self.confidence_threshold
            )

            stats = {
                "word_count": total_words,
                "correction_count": len(corrections),
                "low_confidence_count": low_confidence_count,
                "low_confidence_ratio": (
                    round(low_confidence_count / total_words, 3)
                    if total_words > 0 else 0
                ),
                "average_confidence": (
                    round(sum(w.confidence for w in word_confidences) / total_words, 3)
                    if total_words > 0 else 0
                ),
            }

            return PostProcessResult(
                success=True,
                processed_text=text,
                original_text=original_text,
                word_confidences=word_confidences,
                corrections=corrections,
                stats=stats,
            )

        except Exception as e:
            logger.warning("OCR post-processing failed: %s", e)
            return PostProcessResult(
                success=False,
                processed_text=text,
                original_text=text,
                error=str(e),
            )

    # ------------------------------------------------------------------
    # Pipeline stages
    # ------------------------------------------------------------------

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace: collapse multiple spaces, trim lines."""
        # Collapse multiple spaces (but preserve newlines)
        lines = text.split("\n")
        normalized = []
        for line in lines:
            line = re.sub(r"[ \t]+", " ", line).strip()
            normalized.append(line)

        # Collapse 3+ consecutive empty lines into 2
        result = "\n".join(normalized)
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()

    def _correct_numbers(self, text: str) -> Tuple[str, List[Correction]]:
        """Fix common letter-digit confusion in numeric contexts."""
        corrections = []

        for pattern, replacement in _NUMBER_PATTERNS:
            for match in re.finditer(pattern, text):
                original = match.group()
                if original != replacement:
                    corrections.append(Correction(
                        original=original,
                        corrected=replacement,
                        rule="number_correction",
                        position=match.start(),
                    ))

        # Apply all number corrections
        result = text
        for pattern, replacement in _NUMBER_PATTERNS:
            result = re.sub(pattern, replacement, result)

        # Also fix standalone "O" → "0" when surrounded by digits
        # e.g., "1O0" → "100", "2O24" → "2024"
        def fix_o_in_digits(m):
            word = m.group()
            fixed = ""
            for ch in word:
                if ch in _LETTER_DIGIT_MAP and any(c.isdigit() for c in word):
                    fixed += _LETTER_DIGIT_MAP[ch]
                else:
                    fixed += ch
            if fixed != word:
                corrections.append(Correction(
                    original=word,
                    corrected=fixed,
                    rule="number_letter_mix",
                    position=m.start(),
                ))
            return fixed

        # Match tokens that look like numbers but have letters mixed in
        result = re.sub(
            r"\b[0-9OolIBSZGbqD][0-9OolIBSZGbqD.,]+\b",
            fix_o_in_digits,
            result,
        )

        return result, corrections

    def _correct_vietnamese(self, text: str) -> Tuple[str, List[Correction]]:
        """Fix common Vietnamese OCR diacritics errors."""
        corrections = []

        for pattern, replacement in _VIETNAMESE_CORRECTIONS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                original = match.group()
                if original.lower() != replacement.lower():
                    corrections.append(Correction(
                        original=original,
                        corrected=replacement,
                        rule="vietnamese_diacritics",
                        position=match.start(),
                    ))
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text, corrections

    def _normalize_currency(self, text: str) -> Tuple[str, List[Correction]]:
        """Normalize currency and unit abbreviations."""
        corrections = []

        for pattern, replacement in _CURRENCY_PATTERNS:
            for match in re.finditer(pattern, text):
                original = match.group()
                if original != replacement:
                    corrections.append(Correction(
                        original=original,
                        corrected=replacement,
                        rule="currency_normalization",
                        position=match.start(),
                    ))
            text = re.sub(pattern, replacement, text)

        return text, corrections

    def _score_words(
        self,
        processed_text: str,
        original_text: str,
        corrections: List[Correction],
    ) -> List[WordConfidence]:
        """
        Assign heuristic confidence scores to each word.

        Scoring factors:
        - Word length (very short = lower confidence)
        - Character composition (mixed case anomalies)
        - Whether the word was corrected
        - Dictionary presence (basic check for common words)
        - Special character ratio
        """
        words = processed_text.split()
        corrected_texts = {c.corrected for c in corrections}

        confidences = []
        for word in words:
            score = 1.0
            flags: List[str] = []
            is_corrected = word in corrected_texts
            original = None

            if is_corrected:
                # Find the original text
                for c in corrections:
                    if c.corrected == word:
                        original = c.original
                        break
                score -= 0.15  # Slight penalty for needing correction
                flags.append("corrected")

            # Length penalty (single char words are suspicious unless common)
            if len(word) == 1 and word not in {"a", "I", "ở", "và", "ý", "ư"}:
                score -= 0.2
                flags.append("short")

            # Mixed case anomaly (e.g., "hElLo")
            if (
                len(word) > 2
                and not word.isupper()
                and not word.islower()
                and not word.istitle()
                and not word[0].isupper()
            ):
                score -= 0.15
                flags.append("mixed_case")

            # High special character ratio
            special_count = sum(1 for c in word if not c.isalnum() and c not in ".,;:!?-'\"")
            if len(word) > 0 and special_count / len(word) > 0.5:
                score -= 0.3
                flags.append("special_chars")

            # Repeated characters (e.g., "aaaa")
            if len(word) > 3 and len(set(word.lower())) == 1:
                score -= 0.4
                flags.append("repeated_chars")

            # Numeric but with suspicious characters
            digit_count = sum(1 for c in word if c.isdigit())
            alpha_count = sum(1 for c in word if c.isalpha())
            if digit_count > 0 and alpha_count > 0 and len(word) > 2:
                # Mixed alpha-numeric (could be corrected number)
                if word not in corrected_texts:
                    score -= 0.1
                    flags.append("alpha_numeric_mix")

            # Clamp score
            score = max(0.0, min(1.0, score))

            confidences.append(WordConfidence(
                text=word,
                confidence=score,
                is_corrected=is_corrected,
                original=original,
                flags=flags if flags else [],
            ))

        return confidences
