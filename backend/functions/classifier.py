"""
Classifier function for document classification.

This function classifies documents based on extracted text using LLM or VLM agents.
"""

import json
from typing import List, Optional
from dataclasses import dataclass

from agents import BaseLLMAgent, BaseVLMAgent
from core.utils import strip_code_blocks


@dataclass
class ClassificationRule:
    """Document classification rule."""
    doc_type: str
    description: str


@dataclass
class ClassifyResult:
    """Result of classification operation."""
    success: bool
    document_type: Optional[str] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


class Classifier:
    """
    Classifier for document classification using LLM/VLM agents.
    """
    
    def __init__(self, agent: BaseLLMAgent):
        """
        Initialize classifier.
        
        Args:
            agent: LLM agent for classification
        """
        self.agent = agent
    
    def classify(
        self,
        text: str,
        rules: List[ClassificationRule],
        timeout: int = 60
    ) -> ClassifyResult:
        """
        Classify document based on text and rules.
        
        Args:
            text: Extracted text from document
            rules: List of classification rules
            timeout: Request timeout in seconds
            
        Returns:
            ClassifyResult with document type and confidence
        """
        try:
            # Build prompt
            prompt = self._build_prompt(text, rules)
            
            # Call LLM
            response = self.agent.generate(prompt, timeout=timeout)
            
            if not response.success:
                return ClassifyResult(
                    success=False,
                    error=response.error,
                    error_type=response.error_type
                )
            
            # Parse response
            return self._parse_response(response.content)
            
        except Exception as e:
            return ClassifyResult(
                success=False,
                error=f"Classification failed: {str(e)}",
                error_type="processing_error"
            )
    
    def _build_prompt(self, text: str, rules: List[ClassificationRule]) -> str:
        """Build classification prompt."""
        types_list = "\n".join([
            f"- {rule.doc_type}: {rule.description}"
            for rule in rules
        ])
        
        prompt = f"""Classify this document into one of the following types:

{types_list}

Document text:
{text[:3000]}

Respond in JSON format:
{{
    "document_type": "the matching type",
    "confidence": 0.95,
    "reasoning": "brief explanation"
}}

Respond ONLY with valid JSON."""
        
        return prompt
    
    def _parse_response(self, content: str) -> ClassifyResult:
        """Parse LLM response."""
        try:
            # Remove markdown code blocks
            content = strip_code_blocks(content)
            
            # Parse JSON
            data = json.loads(content)
            
            return ClassifyResult(
                success=True,
                document_type=data.get('document_type'),
                confidence=float(data.get('confidence', 0.0)),
                reasoning=data.get('reasoning', '')
            )
            
        except json.JSONDecodeError as e:
            return ClassifyResult(
                success=False,
                error=f"Failed to parse response: {str(e)}",
                error_type="parsing_error"
            )
