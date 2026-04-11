"""
Splitter function for document chunking.

This function splits documents into categorized chunks based on user-defined categories.
It also supports splitting by document type, identifying page ranges per document type.
"""

import json
import logging
from typing import List, Optional
from dataclasses import dataclass, field

from agents import BaseVLMAgent
from core.utils import strip_code_blocks

logger = logging.getLogger(__name__)


@dataclass
class ChunkCategory:
    """Chunk category definition."""
    name: str
    description: str
    order: int = 0


@dataclass
class Chunk:
    """Document chunk."""
    content: str
    category: str
    page_number: int
    confidence: Optional[float] = None


@dataclass
class DocumentTypeItem:
    """Document type item for document-type splitting results."""
    type_name: str
    page_numbers: List[int] = field(default_factory=list)
    confidence: Optional[float] = None


@dataclass
class SplitResult:
    """Result of split operation."""
    success: bool
    chunks: Optional[List[Chunk]] = None
    unknown_chunks: Optional[List[Chunk]] = None
    document_types: Optional[List[DocumentTypeItem]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


class Splitter:
    """
    Splitter for document chunking using VLM agents.
    """
    
    def __init__(self, agent: BaseVLMAgent):
        """
        Initialize splitter.
        
        Args:
            agent: VLM agent for splitting
        """
        self.agent = agent
    
    def split(
        self,
        file_path: str,
        categories: List[ChunkCategory],
        allow_uncategorized: bool = True,
        timeout: int = 120
    ) -> SplitResult:
        """
        Split document into categorized chunks.
        
        Args:
            file_path: Path to document file
            categories: List of category definitions
            allow_uncategorized: Whether to include unknown chunks
            timeout: Request timeout in seconds
            
        Returns:
            SplitResult with categorized chunks
        """
        try:
            # Build prompt
            prompt = self._build_prompt(categories)
            
            # Call VLM with image(s)
            response = self.agent.generate_from_image(
                file_path,
                prompt,
                timeout=timeout
            )
            
            if not response.success:
                return SplitResult(
                    success=False,
                    error=response.error,
                    error_type=response.error_type
                )
            
            # Parse response
            result = self._parse_response(response.content, categories)
            
            # Filter unknown chunks if not allowed
            if not allow_uncategorized:
                result.unknown_chunks = []
            
            return result
            
        except Exception as e:
            return SplitResult(
                success=False,
                error=f"Split failed: {str(e)}",
                error_type="processing_error"
            )
    
    def _build_prompt(self, categories: List[ChunkCategory]) -> str:
        """Build split prompt."""
        categories_list = "\n".join([
            f"{i+1}. {cat.name}: {cat.description}"
            for i, cat in enumerate(categories)
        ])
        
        prompt = f"""Analyze this document and split it into chunks based on these categories:

{categories_list}

For each section or chunk, assign it to the most appropriate category.
If content doesn't fit any category, mark it as "unknown".

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
        
        return prompt
    
    def _parse_response(
        self,
        content: str,
        categories: List[ChunkCategory]
    ) -> SplitResult:
        """Parse VLM response."""
        try:
            # Remove markdown code blocks
            content = strip_code_blocks(content)
            
            # Parse JSON
            data = json.loads(content)
            
            # Build category name set
            category_names = {cat.name.lower() for cat in categories}
            
            # Separate categorized and unknown chunks
            categorized_chunks = []
            unknown_chunks = []
            
            for chunk_data in data.get('chunks', []):
                content_text = chunk_data.get('content', '')
                category = chunk_data.get('category', 'unknown')
                page_number = chunk_data.get('page_number', 1)
                confidence = chunk_data.get('confidence')
                
                chunk = Chunk(
                    content=content_text,
                    category=category,
                    page_number=page_number,
                    confidence=confidence
                )
                
                if category.lower() in category_names:
                    categorized_chunks.append(chunk)
                else:
                    chunk.category = 'unknown'
                    unknown_chunks.append(chunk)
            
            return SplitResult(
                success=True,
                chunks=categorized_chunks,
                unknown_chunks=unknown_chunks
            )
            
        except json.JSONDecodeError as e:
            return SplitResult(
                success=False,
                error=f"Failed to parse response: {str(e)}",
                error_type="parsing_error"
            )

    def _build_doc_type_prompt(self, categories: List[ChunkCategory]) -> str:
        """Build VLM prompt for document type splitting.

        Constructs a prompt that instructs the VLM to identify document type
        boundaries across pages and return page ranges per document type.

        Args:
            categories: List of user-defined document type categories.

        Returns:
            Prompt string for the VLM agent.
        """
        categories_list = "\n".join([
            f"- {cat.name}: {cat.description}"
            for cat in categories
        ])

        prompt = f"""Analyze this document and identify which pages belong to which document type.

Document type categories:
{categories_list}

Instructions:
- Examine ALL pages of the document.
- Assign each page to exactly one document type from the categories above.
- If a page does not match any of the defined categories, assign it to "Unrecognized".
- Return a JSON array where each element represents a document type found.

Return results in this exact JSON format:
[
  {{
    "type_name": "category name or Unrecognized",
    "page_numbers": [1, 2, 3],
    "confidence": 0.95
  }}
]

Important:
- Every page must be assigned to exactly one document type.
- Use exact category names from the list above.
- Use "Unrecognized" for pages that do not match any category.
- Provide confidence scores between 0.0 and 1.0.
- Page numbers start at 1.

Respond ONLY with valid JSON."""

        return prompt

    def _parse_doc_type_response(
        self,
        content: str,
        categories: List[ChunkCategory],
    ) -> SplitResult:
        """Parse VLM JSON response for document type splitting.

        Strips markdown code blocks, parses the JSON array, maps unrecognized
        type names to "Unrecognized", and returns a SplitResult with
        document_types populated.

        Args:
            content: Raw VLM response string.
            categories: List of user-defined categories for name validation.

        Returns:
            SplitResult with document_types populated.
        """
        try:
            content = strip_code_blocks(content)
            data = json.loads(content)

            # Handle both array and object-with-key formats
            if isinstance(data, dict):
                items = data.get("document_types", [])
            else:
                items = data

            category_names = {cat.name for cat in categories}

            document_types: List[DocumentTypeItem] = []
            for item in items:
                type_name = item.get("type_name", "Unrecognized")
                page_numbers = item.get("page_numbers", [])
                confidence = item.get("confidence")

                # Map unknown type names to "Unrecognized"
                if type_name not in category_names and type_name != "Unrecognized":
                    type_name = "Unrecognized"

                document_types.append(
                    DocumentTypeItem(
                        type_name=type_name,
                        page_numbers=page_numbers,
                        confidence=confidence,
                    )
                )

            return SplitResult(success=True, document_types=document_types)

        except json.JSONDecodeError as e:
            return SplitResult(
                success=False,
                error=f"Failed to parse document type response: {str(e)}",
                error_type="parsing_error",
            )

    def split_by_document_type(
        self,
        file_path: str,
        categories: List[ChunkCategory],
        timeout: int = 120,
    ) -> SplitResult:
        """Split document by document type using VLM agent.

        Builds a doc-type-specific prompt, invokes the VLM agent, and parses
        the response into DocumentTypeItem objects.

        Args:
            file_path: Path to the document file.
            categories: List of document type category definitions.
            timeout: Request timeout in seconds.

        Returns:
            SplitResult with document_types populated.
        """
        try:
            prompt = self._build_doc_type_prompt(categories)

            response = self.agent.generate_from_image(
                file_path,
                prompt,
                timeout=timeout,
            )

            if not response.success:
                return SplitResult(
                    success=False,
                    error=response.error,
                    error_type=response.error_type,
                )

            return self._parse_doc_type_response(response.content, categories)

        except Exception as e:
            return SplitResult(
                success=False,
                error=f"Split failed: {str(e)}",
                error_type="processing_error",
            )

    @staticmethod
    def validate_page_coverage(
        document_types: List[DocumentTypeItem],
        total_pages: int,
    ) -> bool:
        """Validate that every page from 1..total_pages appears in exactly one document type.

        Checks for gaps (missing pages) and overlaps (duplicate pages).
        Logs a warning if validation fails.

        Args:
            document_types: List of DocumentTypeItem objects.
            total_pages: Total number of pages in the document.

        Returns:
            True if every page appears exactly once, False otherwise.
        """
        all_pages: List[int] = []
        for dt in document_types:
            all_pages.extend(dt.page_numbers)

        expected = set(range(1, total_pages + 1))
        actual = set(all_pages)

        # Check for overlaps (duplicates)
        has_overlaps = len(all_pages) != len(actual)
        # Check for gaps
        missing = expected - actual
        # Check for extra pages beyond total
        extra = actual - expected

        if has_overlaps or missing or extra:
            logger.warning(
                "Page coverage validation failed: overlaps=%s, missing_pages=%s, extra_pages=%s",
                has_overlaps,
                sorted(missing) if missing else [],
                sorted(extra) if extra else [],
            )
            return False

        return True
