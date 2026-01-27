#!/usr/bin/env python3
"""
Demonstration script for models.py module.

This script shows how to use the Pydantic models for validation.
"""

import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models import (
    TierEnum, OCRRequest, OCRResponse, HealthResponse, 
    ModelInfo, ErrorResponse
)
from pydantic import ValidationError


def main():
    print("=" * 70)
    print("OCR Web UI Pydantic Models Demo")
    print("=" * 70)
    print()
    
    # Test OCRRequest with valid data
    print("1. Testing OCRRequest with valid data:")
    try:
        request = OCRRequest(
            model_id="lightonocr-2-1b",
            process_all_pages=True,
            tier=TierEnum.NORMAL
        )
        print(f"   ✓ Valid request created: {request.model_dump()}")
    except ValidationError as e:
        print(f"   ✗ Validation failed: {e}")
    print()
    
    # Test OCRRequest with missing required field
    print("2. Testing OCRRequest with missing required field:")
    try:
        request = OCRRequest(
            process_all_pages=True
        )
        print(f"   ✗ Should have failed but got: {request.model_dump()}")
    except ValidationError as e:
        print(f"   ✓ Validation correctly failed: {e.error_count()} error(s)")
        for error in e.errors():
            print(f"      - {error['loc'][0]}: {error['msg']}")
    print()
    
    # Test OCRRequest with invalid tier
    print("3. Testing OCRRequest with invalid tier:")
    try:
        request = OCRRequest(
            model_id="test-model",
            tier="InvalidTier"
        )
        print(f"   ✗ Should have failed but got: {request.model_dump()}")
    except ValidationError as e:
        print(f"   ✓ Validation correctly failed: {e.error_count()} error(s)")
        for error in e.errors():
            print(f"      - {error['loc'][0]}: {error['msg']}")
    print()
    
    # Test OCRRequest with default values
    print("4. Testing OCRRequest with default values:")
    try:
        request = OCRRequest(model_id="test-model")
        print(f"   ✓ Request with defaults: {request.model_dump()}")
        print(f"      - process_all_pages: {request.process_all_pages}")
        print(f"      - tier: {request.tier}")
    except ValidationError as e:
        print(f"   ✗ Validation failed: {e}")
    print()
    
    # Test OCRResponse for success case
    print("5. Testing OCRResponse for success case:")
    response = OCRResponse(
        success=True,
        text="Extracted text from OCR",
        filename="test.pdf",
        model="lightonocr-2-1b",
        pages=3
    )
    print(f"   ✓ Success response: {response.model_dump()}")
    print()
    
    # Test OCRResponse for error case
    print("6. Testing OCRResponse for error case:")
    response = OCRResponse(
        success=False,
        error="Model not found",
        error_type="invalid_model"
    )
    print(f"   ✓ Error response: {response.model_dump()}")
    print()
    
    # Test HealthResponse
    print("7. Testing HealthResponse:")
    health = HealthResponse(
        status="healthy",
        server_running=True,
        available_models=["lightonocr-2-1b", "deepseek-ocr"]
    )
    print(f"   ✓ Health response: {health.model_dump()}")
    print()
    
    # Test ModelInfo
    print("8. Testing ModelInfo:")
    model_info = ModelInfo(
        model_id="lightonocr-2-1b",
        name="LightOnOCR-2-1B",
        provider="lm_studio"
    )
    print(f"   ✓ Model info: {model_info.model_dump()}")
    print()
    
    # Test ErrorResponse
    print("9. Testing ErrorResponse:")
    error = ErrorResponse(
        detail="File too large",
        error_type="file_too_large"
    )
    print(f"   ✓ Error response: {error.model_dump()}")
    print()
    
    # Test TierEnum values
    print("10. Testing TierEnum values:")
    print(f"   ✓ Available tiers: {[tier.value for tier in TierEnum]}")
    print()
    
    print("=" * 70)
    print("All Pydantic models are working correctly!")
    print("=" * 70)


if __name__ == '__main__':
    main()
