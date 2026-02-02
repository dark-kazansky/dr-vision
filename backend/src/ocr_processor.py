"""
OCR processor module for OCR Web UI.

This module handles all OCR processing logic including:
- Image OCR processing
- PDF OCR processing (single and multi-page)
- API communication with OCR providers
- Error handling for various failure scenarios
- Structured data extraction integration

The module is independent of FastAPI/Flask and can be used standalone.

Requirements: 3.2, 5.4, 8.2
"""

import base64
import io
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
import requests
from .extraction_processor import ExtractionProcessor, ExtractionResult
from .models import ExtractionConfig


@dataclass
class OCRResult:
    """Result of OCR processing operation."""
    success: bool
    text: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    pages: Optional[int] = None


class OCRProcessor:
    """
    Handles OCR processing for images and PDFs.
    
    This class encapsulates all OCR processing logic and is independent
    of web framework specifics (FastAPI/Flask).
    """
    
    def __init__(self, model_config: Dict[str, Any]):
        """
        Initialize OCR processor with model configuration.
        
        Args:
            model_config: Dictionary containing:
                - model_id: str - Model identifier
                - base_url: str - API base URL
                - name: str - Display name
                - max_tokens: int - Maximum tokens (default: 4096)
                - temperature: float - Temperature setting (default: 0.2)
                - top_p: float - Top-p sampling (default: 0.9)
        """
        self.model_id = model_config.get('model_id')
        self.base_url = model_config.get('base_url')
        self.name = model_config.get('name', self.model_id)
        self.max_tokens = model_config.get('max_tokens', 4096)
        self.temperature = model_config.get('temperature', 0.2)
        self.top_p = model_config.get('top_p', 0.9)
        
        if not self.model_id or not self.base_url:
            raise ValueError("model_id and base_url are required in model_config")
    
    def process_image(self, image_path: str) -> OCRResult:
        """
        Process OCR on an image file.
        
        Args:
            image_path: Path to the image file (PNG, JPG, JPEG)
            
        Returns:
            OCRResult with success status and extracted text or error
        """
        try:
            # Read and encode image
            with open(image_path, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            # Determine media type from extension
            ext = Path(image_path).suffix.lower()
            media_types = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
            }
            media_type = media_types.get(ext, 'image/png')
            
            # Build API request
            endpoint = f"{self.base_url}/v1/chat/completions"
            payload = {
                "model": self.model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
            }
            
            # Make request
            response = requests.post(endpoint, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            text = result["choices"][0]["message"]["content"]
            
            return OCRResult(success=True, text=text)
            
        except requests.exceptions.ConnectionError as e:
            return OCRResult(
                success=False,
                error=f"LM Studio server is not running. Please start the server at {self.base_url}",
                error_type="connection_error"
            )
        except requests.exceptions.Timeout as e:
            return OCRResult(
                success=False,
                error="Request to LM Studio timed out. The server may be overloaded or not responding.",
                error_type="connection_error"
            )
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') and e.response else 'unknown'
            return OCRResult(
                success=False,
                error=f"LM Studio API error (status {status_code}): {str(e)}",
                error_type="processing_error"
            )
        except requests.exceptions.RequestException as e:
            return OCRResult(
                success=False,
                error=f"Failed to connect to LM Studio: {str(e)}",
                error_type="connection_error"
            )
        except IOError as e:
            return OCRResult(
                success=False,
                error=f"Failed to read file: {str(e)}. The file may be corrupted or inaccessible.",
                error_type="processing_error"
            )
        except KeyError as e:
            return OCRResult(
                success=False,
                error=f"Invalid API response: Missing expected field {str(e)}",
                error_type="processing_error"
            )
        except Exception as e:
            return OCRResult(
                success=False,
                error=f"OCR processing failed: {str(e)}",
                error_type="processing_error"
            )
    
    def process_pdf_page(self, pdf_path: str, page_number: int, render_dpi: int = 200) -> OCRResult:
        """
        Process OCR on a single PDF page.
        
        Args:
            pdf_path: Path to the PDF file
            page_number: Page index (0-based)
            render_dpi: DPI for rendering PDF page (default: 200)
            
        Returns:
            OCRResult with success status and extracted text or error
        """
        try:
            import pypdfium2 as pdfium
        except ImportError:
            return OCRResult(
                success=False,
                error="Missing required dependency: pypdfium2. Please install: pip install pypdfium2",
                error_type="processing_error"
            )
        
        try:
            # Open PDF and render page
            pdf = pdfium.PdfDocument(pdf_path)
            
            # Validate page number
            if page_number < 0 or page_number >= len(pdf):
                return OCRResult(
                    success=False,
                    error=f"Invalid page number: {page_number}. PDF has {len(pdf)} pages.",
                    error_type="processing_error"
                )
            
            page = pdf[page_number]
            
            # Render at specified DPI
            scale = render_dpi / 72
            pil_image = page.render(scale=scale).to_pil()
            
            # Convert PIL image to base64
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Build API request
            endpoint = f"{self.base_url}/v1/chat/completions"
            payload = {
                "model": self.model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
            }
            
            # Make request
            response = requests.post(endpoint, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            text = result["choices"][0]["message"]["content"]
            
            return OCRResult(success=True, text=text)
            
        except requests.exceptions.ConnectionError as e:
            return OCRResult(
                success=False,
                error=f"LM Studio server is not running. Please start the server at {self.base_url}",
                error_type="connection_error"
            )
        except requests.exceptions.Timeout as e:
            return OCRResult(
                success=False,
                error="Request to LM Studio timed out. The server may be overloaded or not responding.",
                error_type="connection_error"
            )
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') and e.response else 'unknown'
            return OCRResult(
                success=False,
                error=f"LM Studio API error (status {status_code}): {str(e)}",
                error_type="processing_error"
            )
        except requests.exceptions.RequestException as e:
            return OCRResult(
                success=False,
                error=f"Failed to connect to LM Studio: {str(e)}",
                error_type="connection_error"
            )
        except IOError as e:
            return OCRResult(
                success=False,
                error=f"Failed to read file: {str(e)}. The file may be corrupted or inaccessible.",
                error_type="processing_error"
            )
        except ValueError as e:
            return OCRResult(
                success=False,
                error=f"Invalid file format: {str(e)}. The file may be corrupted or in an unsupported format.",
                error_type="processing_error"
            )
        except KeyError as e:
            return OCRResult(
                success=False,
                error=f"Invalid API response: Missing expected field {str(e)}",
                error_type="processing_error"
            )
        except Exception as e:
            return OCRResult(
                success=False,
                error=f"OCR processing failed: {str(e)}",
                error_type="processing_error"
            )
    
    def process_pdf_all_pages(self, pdf_path: str, render_dpi: int = 200) -> OCRResult:
        """
        Process OCR on all pages of a PDF.
        
        Args:
            pdf_path: Path to the PDF file
            render_dpi: DPI for rendering PDF pages (default: 200)
            
        Returns:
            OCRResult with success status, combined text from all pages, and page count
        """
        try:
            import pypdfium2 as pdfium
        except ImportError:
            return OCRResult(
                success=False,
                error="Missing required dependency: pypdfium2. Please install: pip install pypdfium2",
                error_type="processing_error"
            )
        
        try:
            # Open PDF and get page count
            pdf = pdfium.PdfDocument(pdf_path)
            page_count = len(pdf)
            
            if page_count == 0:
                return OCRResult(
                    success=False,
                    error="PDF file has no pages",
                    error_type="processing_error"
                )
            
            # Process each page
            all_text = []
            for page_num in range(page_count):
                result = self.process_pdf_page(pdf_path, page_num, render_dpi)
                
                if not result.success:
                    # If any page fails, return the error
                    return result
                
                all_text.append(f"--- Page {page_num + 1} ---\n{result.text}")
            
            # Combine all pages
            combined_text = "\n\n".join(all_text)
            
            return OCRResult(
                success=True,
                text=combined_text,
                pages=page_count
            )
            
        except IOError as e:
            return OCRResult(
                success=False,
                error=f"Failed to read file: {str(e)}. The file may be corrupted or inaccessible.",
                error_type="processing_error"
            )
        except ValueError as e:
            return OCRResult(
                success=False,
                error=f"Invalid file format: {str(e)}. The file may be corrupted or in an unsupported format.",
                error_type="processing_error"
            )
        except Exception as e:
            return OCRResult(
                success=False,
                error=f"OCR processing failed: {str(e)}",
                error_type="processing_error"
            )

    def process_with_extraction(
        self,
        file_path: str,
        extraction_config: ExtractionConfig,
        extraction_model: str = "qwen3-max",
        render_dpi: int = 200,
        timeout: int = 60
    ) -> ExtractionResult:
        """
        Process file with OCR and then extract structured data.
        
        Args:
            file_path: Path to the file (image or PDF)
            extraction_config: Extraction configuration with schema and target
            extraction_model: Poe model to use for extraction (assistant, qwen3-max, gemini-3-pro)
            render_dpi: DPI for rendering PDF pages (default: 200)
            timeout: Timeout in seconds for LLM API call (default: 60)
            
        Returns:
            ExtractionResult with success status and extracted structured data or error
        """
        try:
            # Determine file type
            ext = Path(file_path).suffix.lower()
            
            # Process OCR first
            if ext in ['.png', '.jpg', '.jpeg']:
                ocr_result = self.process_image(file_path)
            elif ext == '.pdf':
                # For extraction, always process all pages to get complete context
                ocr_result = self.process_pdf_all_pages(file_path, render_dpi)
            else:
                return ExtractionResult(
                    success=False,
                    error=f"Unsupported file type: {ext}",
                    error_type="processing_error"
                )
            
            # Check if OCR was successful
            if not ocr_result.success:
                return ExtractionResult(
                    success=False,
                    error=f"OCR failed: {ocr_result.error}",
                    error_type=ocr_result.error_type
                )
            
            # Create extraction processor with specified model
            extractor = ExtractionProcessor(extraction_model)
            
            # Extract structured data with timeout
            extraction_result = extractor.extract_from_text(
                ocr_result.text,
                extraction_config,
                timeout=timeout
            )
            
            return extraction_result
            
        except Exception as e:
            return ExtractionResult(
                success=False,
                error=f"Extraction processing failed: {str(e)}",
                error_type="processing_error"
            )
