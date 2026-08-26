"""
LM Studio OCR Agent implementation.

Implements BaseOCRAgent for LM Studio (DeepSeek-OCR, Nanonets-OCR2-3B).
"""

import base64
import io
import requests
from pathlib import Path
from typing import Optional
from agents.base_ocr_agent import BaseOCRAgent, OCRResponse


class LMStudioOCRAgent(BaseOCRAgent):
    """
    LM Studio OCR Agent for local OCR models.
    
    Supports: DeepSeek-OCR, Nanonets-OCR2-3B via LM Studio.
    """
    
    def process_image(
        self,
        image_path: str,
        timeout: int = 120
    ) -> OCRResponse:
        """
        Process OCR on an image file.
        
        Args:
            image_path: Path to image file
            timeout: Request timeout in seconds
            
        Returns:
            OCRResponse with extracted text or error
        """
        try:
            # Read and encode image
            with open(image_path, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            # Determine media type
            ext = Path(image_path).suffix.lower()
            media_types = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
            }
            media_type = media_types.get(ext, 'image/png')
            
            # Build API request
            endpoint = f"{self.base_url}/v1/chat/completions"
            
            # For non-LightOnOCR models, include text prompt
            payload = {
                "model": self.model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all text from this image. Provide the text exactly as it appears, maintaining the original formatting and structure."
                            },
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
            response = requests.post(endpoint, json=payload, timeout=timeout)
            
            # Check status
            if response.status_code != 200:
                error_detail = f"HTTP {response.status_code}"
                try:
                    error_json = response.json()
                    if 'error' in error_json:
                        if isinstance(error_json['error'], dict):
                            error_detail = f"{error_detail}: {error_json['error'].get('message', str(error_json['error']))}"
                        else:
                            error_detail = f"{error_detail}: {error_json['error']}"
                except:
                    error_detail = f"{error_detail}: {response.text[:200]}"
                
                return OCRResponse(
                    success=False,
                    error=f"LM Studio error: {error_detail}",
                    error_type="api_error"
                )
            
            result = response.json()
            
            # Validate response
            if "choices" not in result or len(result["choices"]) == 0:
                return OCRResponse(
                    success=False,
                    error="Invalid LM Studio response: Missing or empty 'choices' field",
                    error_type="api_error"
                )
            
            if "message" not in result["choices"][0] or "content" not in result["choices"][0]["message"]:
                return OCRResponse(
                    success=False,
                    error="Invalid LM Studio response: Missing 'content' field",
                    error_type="api_error"
                )
            
            text = result["choices"][0]["message"]["content"]
            
            return OCRResponse(
                success=True,
                text=text,
                pages=1,
                metadata={'model': self.model_id}
            )
            
        except requests.exceptions.ConnectionError as e:
            return OCRResponse(
                success=False,
                error=f"LM Studio server is not running at {self.base_url}",
                error_type="connection_error"
            )
        except requests.exceptions.Timeout as e:
            return OCRResponse(
                success=False,
                error=f"Request timed out after {timeout} seconds",
                error_type="timeout_error"
            )
        except IOError as e:
            return OCRResponse(
                success=False,
                error=f"Failed to read image file: {str(e)}",
                error_type="file_error"
            )
        except Exception as e:
            return OCRResponse(
                success=False,
                error=f"OCR processing failed: {str(e)}",
                error_type="processing_error"
            )
    
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
            render_dpi: DPI for rendering
            timeout: Request timeout in seconds
            
        Returns:
            OCRResponse with extracted text or error
        """
        try:
            import pypdfium2 as pdfium
        except ImportError:
            return OCRResponse(
                success=False,
                error="Missing required dependency: pypdfium2",
                error_type="dependency_error"
            )
        
        try:
            # Open PDF and render page
            pdf = pdfium.PdfDocument(pdf_path)
            
            if page_number < 0 or page_number >= len(pdf):
                return OCRResponse(
                    success=False,
                    error=f"Invalid page number: {page_number}. PDF has {len(pdf)} pages.",
                    error_type="validation_error"
                )
            
            page = pdf[page_number]
            scale = render_dpi / 72
            pil_image = page.render(scale=scale).to_pil()
            
            # Convert to base64
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
                                "type": "text",
                                "text": "Extract all text from this image. Provide the text exactly as it appears, maintaining the original formatting and structure."
                            },
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
            
            response = requests.post(endpoint, json=payload, timeout=timeout)
            
            if response.status_code != 200:
                return OCRResponse(
                    success=False,
                    error=f"LM Studio error: HTTP {response.status_code}",
                    error_type="api_error"
                )
            
            result = response.json()
            text = result["choices"][0]["message"]["content"]
            
            return OCRResponse(
                success=True,
                text=text,
                pages=1,
                metadata={'model': self.model_id, 'page': page_number}
            )
            
        except Exception as e:
            return OCRResponse(
                success=False,
                error=f"PDF page OCR failed: {str(e)}",
                error_type="processing_error"
            )
    
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
            render_dpi: DPI for rendering
            timeout: Request timeout in seconds
            
        Returns:
            OCRResponse with combined text or error
        """
        try:
            import pypdfium2 as pdfium
        except ImportError:
            return OCRResponse(
                success=False,
                error="Missing required dependency: pypdfium2",
                error_type="dependency_error"
            )
        
        try:
            pdf = pdfium.PdfDocument(pdf_path)
            page_count = len(pdf)
            
            if page_count == 0:
                return OCRResponse(
                    success=False,
                    error="PDF file has no pages",
                    error_type="validation_error"
                )
            
            all_text = []
            for page_num in range(page_count):
                result = self.process_pdf_page(pdf_path, page_num, render_dpi, timeout)
                
                if not result.success:
                    return result
                
                all_text.append(f"--- Page {page_num + 1} ---\n{result.text}")
            
            combined_text = "\n\n".join(all_text)
            
            return OCRResponse(
                success=True,
                text=combined_text,
                pages=page_count,
                metadata={'model': self.model_id}
            )
            
        except Exception as e:
            return OCRResponse(
                success=False,
                error=f"PDF OCR failed: {str(e)}",
                error_type="processing_error"
            )
