"""
Splitter function for document chunking.

This function splits documents into categorized chunks based on user-defined categories.
"""

import json
from typing import List, Optional
from dataclasses import dataclass

from agents import BaseVLMAgent


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
class SplitResult:
    """Result of split operation."""
    success: bool
    chunks: Optional[List[Chunk]] = None
    unknown_chunks: Optional[List[Chunk]] = None
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
            if content.startswith('```'):
                lines = content.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                content = '\n'.join(lines).strip()
            
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
