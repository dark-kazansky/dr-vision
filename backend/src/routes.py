"""
FastAPI route handlers for OCR Web UI.

This module defines all API endpoints and delegates business logic
to the appropriate modules (OCRProcessor, utils, config).

Requirements: 3.1, 3.4, 5.1, 9.1, 9.4, 9.6, 9.8, 12.1, 12.2, 12.3
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import os

from .config import Config, ConfigurationError
from .models import OCRResponse, HealthResponse, ErrorResponse, TierEnum
from .ocr_processor import OCRProcessor
from .utils import allowed_file, get_file_type, check_server_status, secure_save_file


# Create API router
router = APIRouter()


# Dependency injection for configuration
def get_config() -> Config:
    """
    Dependency injection function for configuration access.
    
    Returns:
        Config instance
        
    Raises:
        HTTPException: If configuration cannot be loaded
    """
    try:
        return Config.load()
    except ConfigurationError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")


@router.post("/ocr", response_model=OCRResponse)
async def process_ocr(
    file: UploadFile = File(...),
    model_id: str = Form(...),
    process_all_pages: bool = Form(False),
    tier: TierEnum = Form(TierEnum.NORMAL),
    config: Config = Depends(get_config)
) -> OCRResponse:
    """
    Process OCR on uploaded file.
    
    Args:
        file: Uploaded file (image or PDF)
        model_id: Model ID to use for OCR processing
        process_all_pages: Whether to process all pages of PDF (default: False)
        tier: Processing tier (Rapid, Normal, or Advance)
        config: Configuration instance (injected)
        
    Returns:
        OCRResponse with success status and extracted text or error
        
    Raises:
        HTTPException: For various error conditions (400, 413, 500)
    """
    # Validate file was provided
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected"
        )
    
    # Validate file extension
    upload_config = config.upload_config
    allowed_extensions = set(upload_config.get('allowed_extensions', []))
    
    if not allowed_file(file.filename, allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Validate file size
    max_size_mb = upload_config.get('max_size_mb', 10)
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # Read file to check size
    file_content = await file.read()
    if len(file_content) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds maximum allowed size of {max_size_mb}MB"
        )
    
    # Reset file pointer for saving
    await file.seek(0)
    
    # Validate model
    model_config = config.get_model_config(model_id)
    if not model_config:
        available_models = config.get_available_models()
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model: {model_id}. Available models: {', '.join(available_models)}"
        )
    
    # Save file securely
    upload_folder = upload_config.get('folder', 'uploads')
    try:
        file_path = await secure_save_file(file, upload_folder)
    except (ValueError, IOError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )
    
    try:
        # Determine file type
        file_type = get_file_type(file.filename)
        if not file_type:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type"
            )
        
        # Create OCR processor
        processor = OCRProcessor({
            'model_id': model_config.model_id,
            'base_url': model_config.base_url,
            'name': model_config.name,
            'max_tokens': model_config.max_tokens,
            'temperature': model_config.temperature,
            'top_p': model_config.top_p
        })
        
        # Get PDF configuration
        pdf_config = config.pdf_config
        render_dpi = pdf_config.get('render_dpi', 200)
        
        # Process based on file type
        if file_type == 'image':
            result = processor.process_image(file_path)
        elif file_type == 'pdf':
            if process_all_pages:
                result = processor.process_pdf_all_pages(file_path, render_dpi)
            else:
                result = processor.process_pdf_page(file_path, 0, render_dpi)
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type"
            )
        
        # Build response
        if result.success:
            return OCRResponse(
                success=True,
                text=result.text,
                filename=file.filename,
                model=model_id,
                pages=result.pages
            )
        else:
            # Return error response with 500 status
            raise HTTPException(
                status_code=500,
                detail=result.error
            )
            
    finally:
        # Clean up uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)


@router.get("/health", response_model=HealthResponse)
async def health_check(config: Config = Depends(get_config)) -> HealthResponse:
    """
    Health check endpoint.
    
    Returns server status and available models.
    
    Args:
        config: Configuration instance (injected)
        
    Returns:
        HealthResponse with status and available models
    """
    # Get available models
    available_models = config.get_available_models()
    
    # Check if any API provider is running
    # For now, check the first provider (lm_studio)
    providers = config.api_providers
    server_running = False
    
    if providers:
        # Get first provider's base URL
        first_provider = list(providers.values())[0]
        base_url = first_provider.get('base_url')
        
        if base_url:
            status = check_server_status(base_url)
            server_running = status.get('running', False)
    
    # Determine overall status
    if server_running and available_models:
        status = "healthy"
    elif available_models:
        status = "degraded"
    else:
        status = "unhealthy"
    
    return HealthResponse(
        status=status,
        server_running=server_running,
        available_models=available_models
    )
