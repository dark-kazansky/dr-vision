"""
VLM to OCR Adapter.

This adapter wraps VLM agents to provide the OCR agent interface.
Allows using VLM agents (Google, POE, etc.) for OCR tasks through the Parser.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional
from PIL import Image
import pypdfium2 as pdfium

from agents.base_ocr_agent import BaseOCRAgent, OCRResponse
from agents.base_vlm_agent import BaseVLMAgent
from core.prompts import PromptTemplates


class VLMOCRAdapter(BaseOCRAgent):
    """
    Adapter that wraps a VLM agent to provide OCR agent interface.
    
    This allows VLM agents (which use generate_from_image) to be used
    wherever OCR agents (which use process_image) are expected.
    """
    
    def __init__(
        self,
        vlm_agent: BaseVLMAgent,
        use_system_prompt: bool = True,
        **kwargs
    ):
        """
        Initialize VLM-to-OCR adapter.
        
        Args:
            vlm_agent: VLM agent to wrap
            use_system_prompt: Whether to use system prompts for better OCR
            **kwargs: Additional parameters (ignored, for compatibility)
        """
        # Initialize base with VLM agent's config
        super().__init__(
            model_id=vlm_agent.model_id,
            base_url="",  # VLM agents don't use base_url
            max_tokens=vlm_agent.max_tokens,
            temperature=vlm_agent.temperature,
            top_p=vlm_agent.top_p
        )
        
        self.vlm_agent = vlm_agent
        self.use_system_prompt = use_system_prompt
        
        # Detect model type for prompts
        self.model_type = PromptTemplates.detect_model_type(vlm_agent.model_id)
    
    def process_image(
        self,
        image_path: str,
        timeout: int = 120
    ) -> OCRResponse:
        """
        Process OCR on an image file using VLM agent.
        
        Args:
            image_path: Path to image file (PNG, JPG, JPEG)
            timeout: Request timeout in seconds
            
        Returns:
            OCRResponse with extracted text or error
        """
        try:
            # Get OCR prompt
            prompt = PromptTemplates.get_ocr_prompt(self.model_type)
            
            # Get system prompt if enabled
            system_prompt = None
            if self.use_system_prompt:
                system_prompt = PromptTemplates.get_system_prompt(self.model_type, "ocr")
            
            # Use VLM agent to generate text from image
            result = self.vlm_agent.generate_from_image(
                image_path=image_path,
                prompt=prompt,
                system_prompt=system_prompt,
                timeout=timeout
            )
            
            if not result.success:
                return OCRResponse(
                    success=False,
                    error=result.error,
                    error_type=result.error_type
                )
            
            return OCRResponse(
                success=True,
                text=result.content,
                pages=1,
                metadata={
                    'model': self.model_id,
                    'adapter': 'vlm_ocr_adapter',
                    'vlm_metadata': result.metadata
                }
            )
            
        except Exception as e:
            return OCRResponse(
                success=False,
                error=f"VLM OCR adapter failed: {str(e)}",
                error_type="adapter_error"
            )
    
    def process_pdf_page(
        self,
        pdf_path: str,
        page_number: int,
        render_dpi: int = 200,
        timeout: int = 120
    ) -> OCRResponse:
        """
        Process OCR on a single PDF page using VLM agent.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page index (0-based)
            render_dpi: DPI for rendering PDF page
            timeout: Request timeout in seconds
            
        Returns:
            OCRResponse with extracted text or error
        """
        temp_image_path = None
        
        try:
            # Render PDF page to image
            pdf = pdfium.PdfDocument(pdf_path)
            
            if page_number >= len(pdf):
                return OCRResponse(
                    success=False,
                    error=f"Page {page_number} does not exist (PDF has {len(pdf)} pages)",
                    error_type="validation_error"
                )
            
            page = pdf[page_number]
            
            # Render to PIL Image
            pil_image = page.render(
                scale=render_dpi / 72.0,
                rotation=0
            ).to_pil()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                temp_image_path = tmp.name
                pil_image.save(temp_image_path, 'PNG')
            
            # Process image using VLM
            result = self.process_image(temp_image_path, timeout)
            
            if result.success and result.metadata:
                result.metadata['page_number'] = page_number
                result.metadata['pdf_path'] = pdf_path
            
            return result
            
        except Exception as e:
            return OCRResponse(
                success=False,
                error=f"PDF page processing failed: {str(e)}",
                error_type="processing_error"
            )
        
        finally:
            # Clean up temporary image
            if temp_image_path and os.path.exists(temp_image_path):
                try:
                    os.remove(temp_image_path)
                except:
                    pass
    
    def process_pdf_all_pages(
        self,
        pdf_path: str,
        render_dpi: int = 200,
        timeout: int = 120
    ) -> OCRResponse:
        """
        Process OCR on all pages of a PDF using VLM agent.
        
        Args:
            pdf_path: Path to PDF file
            render_dpi: DPI for rendering PDF pages
            timeout: Request timeout in seconds
            
        Returns:
            OCRResponse with combined text from all pages or error
        """
        try:
            # Get page count
            pdf = pdfium.PdfDocument(pdf_path)
            page_count = len(pdf)
            
            if page_count == 0:
                return OCRResponse(
                    success=False,
                    error="PDF has no pages",
                    error_type="validation_error"
                )
            
            # Process each page
            all_text = []
            for page_num in range(page_count):
                result = self.process_pdf_page(
                    pdf_path=pdf_path,
                    page_number=page_num,
                    render_dpi=render_dpi,
                    timeout=timeout
                )
                
                if not result.success:
                    return OCRResponse(
                        success=False,
                        error=f"Failed to process page {page_num + 1}: {result.error}",
                        error_type=result.error_type
                    )
                
                all_text.append(f"--- Page {page_num + 1} ---\n{result.text}")
            
            # Combine all pages
            combined_text = "\n\n".join(all_text)
            
            return OCRResponse(
                success=True,
                text=combined_text,
                pages=page_count,
                metadata={
                    'model': self.model_id,
                    'adapter': 'vlm_ocr_adapter',
                    'pdf_path': pdf_path,
                    'page_count': page_count
                }
            )
            
        except Exception as e:
            return OCRResponse(
                success=False,
                error=f"PDF processing failed: {str(e)}",
                error_type="processing_error"
            )
