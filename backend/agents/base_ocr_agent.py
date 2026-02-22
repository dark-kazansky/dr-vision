"""
Base OCR Agent for specialized OCR models.

All OCR agents (LM Studio, vLLM) inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OCRResponse:
    """Response from OCR agent."""
    success: bool
    text: Optional[str] = None
    pages: Optional[int] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseOCRAgent(ABC):
    """
    Base class for all OCR agents.
    
    This abstract class defines the interface that all OCR implementations
    must follow (LM Studio, vLLM, etc.).
    """
    
    def __init__(
        self,
        model_id: str,
        base_url: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        top_p: float = 0.9,
        **kwargs
    ):
        """
        Initialize OCR agent.
        
        Args:
            model_id: Model identifier
            base_url: API base URL
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            top_p: Top-p sampling parameter
            **kwargs: Additional model-specific parameters
        """
        self.model_id = model_id
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.extra_params = kwargs
    
    @abstractmethod
    def process_image(
        self,
        image_path: str,
        timeout: int = 120
    ) -> OCRResponse:
        """
        Process OCR on an image file.
        
        Args:
            image_path: Path to image file (PNG, JPG, JPEG)
            timeout: Request timeout in seconds
            
        Returns:
            OCRResponse with extracted text or error
        """
        pass
    
    @abstractmethod
    def process_pdf_page(
        self,
        pdf_path: str,
        page_number: int,
        render_dpi: int = 200,
        timeout: int = 120
    ) -> OCRResponse:
        """
        Process OCR on a single PDF page.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page index (0-based)
            render_dpi: DPI for rendering PDF page
            timeout: Request timeout in seconds
            
        Returns:
            OCRResponse with extracted text or error
        """
        pass
    
    @abstractmethod
    def process_pdf_all_pages(
        self,
        pdf_path: str,
        render_dpi: int = 200,
        timeout: int = 120
    ) -> OCRResponse:
        """
        Process OCR on all pages of a PDF.
        
        Args:
            pdf_path: Path to PDF file
            render_dpi: DPI for rendering PDF pages
            timeout: Request timeout in seconds
            
        Returns:
            OCRResponse with combined text from all pages or error
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Validate agent configuration.
        
        Returns:
            True if configuration is valid
        """
        if not self.model_id or not self.base_url:
            return False
        if self.temperature < 0 or self.temperature > 1:
            return False
        if self.max_tokens <= 0:
            return False
        return True
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get agent configuration.
        
        Returns:
            Dictionary with agent configuration
        """
        return {
            'model_id': self.model_id,
            'base_url': self.base_url,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'top_p': self.top_p,
            **self.extra_params
        }
    
    def check_server_status(self) -> bool:
        """
        Check if OCR server is running.
        
        Returns:
            True if server is accessible
        """
        try:
            import requests
            response = requests.get(self.base_url, timeout=5)
            return True
        except:
            return False
