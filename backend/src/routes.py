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
from .models import OCRResponse, HealthResponse, ErrorResponse, TierEnum, ExtractionConfig, SchemaField
from .ocr_processor import OCRProcessor
from .schema_generation_engine import SchemaGenerationEngine
from .utils import allowed_file, get_file_type, check_server_status, secure_save_file
import json
from pydantic import ValidationError


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
    extraction_enabled: bool = Form(False),
    extraction_target: Optional[str] = Form(None),
    extraction_schema: Optional[str] = Form(None),
    extractor_model: Optional[str] = Form(None),
    extractor_tier: Optional[str] = Form(None),
    config: Config = Depends(get_config)
) -> OCRResponse:
    """
    Process OCR on uploaded file with optional structured data extraction.
    
    Args:
        file: Uploaded file (image or PDF)
        model_id: Model ID to use for OCR processing
        process_all_pages: Whether to process all pages of PDF (default: False)
        tier: Processing tier for OCR (Rapid, Normal, or Advance)
        extraction_enabled: Whether to enable structured data extraction (default: False)
        extraction_target: Extraction target scope (document, page, or table_row)
        extraction_schema: JSON string containing extraction schema definition
        extractor_model: Poe model to use for extraction (assistant, qwen3-max, gemini-3-pro)
        extractor_tier: Extraction tier (Rapid, Normal, or Advance)
        config: Configuration instance (injected)
        
    Returns:
        OCRResponse with success status and extracted text or structured data
        
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
    
    # Parse and validate extraction config if enabled
    extraction_config = None
    if extraction_enabled:
        if not extraction_schema or not extraction_target:
            raise HTTPException(
                status_code=400,
                detail="extraction_target and extraction_schema are required when extraction_enabled is True"
            )
        
        try:
            # Parse the JSON schema string
            schema_data = json.loads(extraction_schema)
            
            # Create ExtractionConfig with the parsed schema
            extraction_config = ExtractionConfig(
                enabled=True,
                target=extraction_target,
                schema=schema_data
            )
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid extraction_schema JSON: {str(e)}"
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid extraction configuration: {str(e)}"
            )
    
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
            # If extraction is enabled, route to extraction processing
            if extraction_config:
                try:
                    # Use provided extractor_model or fall back to tier mapping
                    if extractor_model:
                        extraction_model = extractor_model
                    else:
                        # Map tier to Poe extraction model (fallback)
                        tier_to_extraction_model = {
                            'Rapid': 'assistant',
                            'Normal': 'qwen3-max',
                            'Advance': 'gemini-3-pro'
                        }
                        extraction_model = tier_to_extraction_model.get(tier.value, 'qwen3-max')
                    
                    # Process with extraction
                    extraction_result = processor.process_with_extraction(
                        file_path, 
                        extraction_config,
                        extraction_model,
                        render_dpi
                    )
                    
                    if extraction_result.success:
                        return OCRResponse(
                            success=True,
                            text=result.text,
                            structured_data=extraction_result.structured_data,
                            extraction_config=extraction_config.model_dump(),
                            field_errors=extraction_result.field_errors,
                            filename=file.filename,
                            model=model_id,
                            pages=result.pages
                        )
                    else:
                        # Determine appropriate HTTP status code based on error type
                        if extraction_result.error_type == "timeout_error":
                            # Return 504 Gateway Timeout for LLM timeout errors
                            # Include partial results if available
                            raise HTTPException(
                                status_code=504,
                                detail={
                                    "error": extraction_result.error,
                                    "error_type": extraction_result.error_type,
                                    "partial_results": extraction_result.partial_results
                                }
                            )
                        elif extraction_result.error_type in ["validation_error", "parsing_error"]:
                            # Return 400 for validation/parsing errors with details
                            raise HTTPException(
                                status_code=400,
                                detail={
                                    "error": extraction_result.error,
                                    "error_type": extraction_result.error_type,
                                    "partial_results": extraction_result.partial_results
                                }
                            )
                        else:
                            # Return 500 for other processing errors with details
                            # Include partial results when possible
                            raise HTTPException(
                                status_code=500,
                                detail={
                                    "error": extraction_result.error,
                                    "error_type": extraction_result.error_type,
                                    "partial_results": extraction_result.partial_results
                                }
                            )
                except HTTPException:
                    # Re-raise HTTP exceptions
                    raise
                except Exception as e:
                    # Catch any unexpected exceptions and return 500
                    raise HTTPException(
                        status_code=500,
                        detail={
                            "error": f"Extraction processing failed: {str(e)}",
                            "error_type": "processing_error"
                        }
                    )
            else:
                # Standard OCR response without extraction
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



@router.post("/generate-schema")
async def generate_schema(
    prompt: str = Form(...),
    file: Optional[UploadFile] = File(None),
    model_id: Optional[str] = Form("qwen3-max"),
    config: Config = Depends(get_config)
) -> JSONResponse:
    """
    Generate extraction schema automatically using AI based on user prompt and optional sample file.
    
    Args:
        prompt: User's description of what data to extract
        file: Optional sample document file (image or PDF) to analyze
        model_id: Poe model to use for generation (assistant, qwen3-max, gemini-3-pro)
        config: Configuration instance (injected)
        
    Returns:
        JSONResponse with generated schema fields or error
        
    Raises:
        HTTPException: For various error conditions (400, 500)
    """
    # Validate prompt is not empty
    if not prompt or not prompt.strip():
        raise HTTPException(
            status_code=400,
            detail="Prompt is required and cannot be empty"
        )
    
    sample_text = None
    file_path = None
    
    try:
        # If file is provided, process it to extract text
        if file and file.filename:
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
            
            # Save file securely
            upload_folder = upload_config.get('folder', 'uploads')
            try:
                file_path = await secure_save_file(file, upload_folder)
            except (ValueError, IOError) as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to save file: {str(e)}"
                )
            
            # Extract text from file using OCR
            try:
                # Get default model for OCR
                default_model_id = config.get_available_models()[0] if config.get_available_models() else None
                if not default_model_id:
                    raise HTTPException(
                        status_code=500,
                        detail="No OCR models available"
                    )
                
                model_config = config.get_model_config(default_model_id)
                if not model_config:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to get model configuration"
                    )
                
                # Create OCR processor
                from .ocr_processor import OCRProcessor
                processor = OCRProcessor({
                    'model_id': model_config.model_id,
                    'base_url': model_config.base_url,
                    'name': model_config.name,
                    'max_tokens': model_config.max_tokens,
                    'temperature': model_config.temperature,
                    'top_p': model_config.top_p
                })
                
                # Determine file type and process
                file_type = get_file_type(file.filename)
                if file_type == 'image':
                    result = processor.process_image(file_path)
                elif file_type == 'pdf':
                    # For schema generation, just process first page
                    pdf_config = config.pdf_config
                    render_dpi = pdf_config.get('render_dpi', 200)
                    result = processor.process_pdf_page(file_path, 0, render_dpi)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid file type"
                    )
                
                if result.success:
                    sample_text = result.text
                else:
                    # If OCR fails, continue without sample text
                    sample_text = None
                    
            except Exception as e:
                # If OCR fails, continue without sample text
                sample_text = None
        
        # Create schema generation engine
        try:
            engine = SchemaGenerationEngine(model_id=model_id)
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
        
        # Generate schema
        generation_result = engine.generate_schema(prompt, sample_text)
        
        if generation_result.success:
            # Convert SchemaField objects to dictionaries
            schema_dicts = [
                {
                    "name": field.name,
                    "type": field.type.value,
                    "description": field.description,
                    "required": field.required
                }
                for field in generation_result.schema
            ]
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "schema": schema_dicts
                }
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Schema generation failed: {generation_result.error}"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Schema generation failed: {str(e)}"
        )
    finally:
        # Clean up uploaded file if it exists
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
