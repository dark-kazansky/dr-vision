"""
Template Matcher — Auto-detect document type and match to best extraction template.

Matching strategy (scored, highest wins):
1. Keyword matching: count template keywords found in document text
2. Document type matching: if document was already classified, direct match
3. Combined score: keyword_score * 0.6 + classification_score * 0.4

The matcher does NOT perform OCR — it expects pre-extracted text as input.
Typically chained after a parse step in the workflow pipeline.
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from services.template_service import ExtractionTemplate, template_service

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of template matching."""

    template_id: str
    template_name: str
    document_type: str
    confidence: float  # 0.0 - 1.0
    keyword_hits: int
    total_keywords: int
    matched_keywords: List[str]

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "template_name": self.template_name,
            "document_type": self.document_type,
            "confidence": round(self.confidence, 3),
            "keyword_hits": self.keyword_hits,
            "total_keywords": self.total_keywords,
            "matched_keywords": self.matched_keywords,
        }


@dataclass
class MatchResponse:
    """Full response from template matching."""

    success: bool
    best_match: Optional[MatchResult] = None
    all_matches: List[MatchResult] = None  # type: ignore
    no_match_reason: Optional[str] = None

    def __post_init__(self):
        if self.all_matches is None:
            self.all_matches = []

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "best_match": self.best_match.to_dict() if self.best_match else None,
            "all_matches": [m.to_dict() for m in self.all_matches],
            "match_count": len(self.all_matches),
            "no_match_reason": self.no_match_reason,
        }


class TemplateMatcher:
    """
    Matches document text against available templates.

    Usage:
        matcher = TemplateMatcher()
        result = matcher.match("... document text ...")
        if result.best_match:
            template = template_service.get(result.best_match.template_id)
            # Use template.extraction_schema for extraction
    """

    def __init__(
        self,
        min_confidence: float = 0.15,
        max_results: int = 5,
    ):
        """
        Args:
            min_confidence: Minimum score to consider a match (0.0 - 1.0)
            max_results: Maximum number of matches to return
        """
        self.min_confidence = min_confidence
        self.max_results = max_results

    def match(
        self,
        text: str,
        document_type: Optional[str] = None,
        templates: Optional[List[ExtractionTemplate]] = None,
    ) -> MatchResponse:
        """
        Match document text to the best template.

        Args:
            text: Document text (from OCR/parsing)
            document_type: Pre-classified document type (if available)
            templates: Optional list of templates to match against
                      (defaults to all templates in template_service)

        Returns:
            MatchResponse with best match and ranked alternatives
        """
        if not text or not text.strip():
            return MatchResponse(
                success=False,
                no_match_reason="Empty document text",
            )

        if templates is None:
            templates = template_service.list_all()

        if not templates:
            return MatchResponse(
                success=False,
                no_match_reason="No templates available",
            )

        # Score each template
        scored: List[Tuple[float, MatchResult]] = []
        text_lower = text.lower()

        for template in templates:
            score, result = self._score_template(template, text_lower, document_type)
            if score >= self.min_confidence:
                scored.append((score, result))

        if not scored:
            return MatchResponse(
                success=True,
                no_match_reason="No template matched above confidence threshold",
            )

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        all_matches = [r for _, r in scored[: self.max_results]]
        best_match = all_matches[0] if all_matches else None

        return MatchResponse(
            success=True,
            best_match=best_match,
            all_matches=all_matches,
        )

    def match_by_type(self, document_type: str) -> Optional[ExtractionTemplate]:
        """Direct match by document_type (exact match)."""
        for template in template_service.list_all():
            if template.document_type.lower() == document_type.lower():
                return template
        return None

    def _score_template(
        self,
        template: ExtractionTemplate,
        text_lower: str,
        classified_type: Optional[str],
    ) -> Tuple[float, MatchResult]:
        """
        Score a single template against document text.

        Returns (score, MatchResult).
        """
        # 1. Keyword matching (60% weight)
        keywords = template.match_rules.get("keywords", [])
        keyword_hits = 0
        matched_keywords: List[str] = []

        for kw in keywords:
            # Use word boundary-aware search
            pattern = re.escape(kw.lower())
            if re.search(pattern, text_lower):
                keyword_hits += 1
                matched_keywords.append(kw)

        keyword_score = (keyword_hits / len(keywords)) if keywords else 0

        # 2. Classification matching (40% weight)
        classification_score = 0.0
        if classified_type and template.document_type:
            if classified_type.lower() == template.document_type.lower():
                classification_score = 1.0
            elif classified_type.lower() in template.document_type.lower():
                classification_score = 0.7

        # 3. Combined score
        if keywords and classified_type:
            score = keyword_score * 0.6 + classification_score * 0.4
        elif keywords:
            score = keyword_score
        elif classified_type:
            score = classification_score
        else:
            score = 0.0

        result = MatchResult(
            template_id=template.template_id,
            template_name=template.name,
            document_type=template.document_type,
            confidence=score,
            keyword_hits=keyword_hits,
            total_keywords=len(keywords),
            matched_keywords=matched_keywords,
        )

        return score, result


# Module-level singleton
template_matcher = TemplateMatcher()
