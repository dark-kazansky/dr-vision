#!/usr/bin/env python3
"""
Test script for model configuration retrieval.

This script tests the get_model_config() method and model-related functionality.
"""

import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config import Config


def main():
    print("=" * 70)
    print("Model Configuration Retrieval Tests")
    print("=" * 70)
    print()
    
    # Load configuration
    config = Config.load('backend/config/config.yaml')
    
    # Test 1: Get existing model configuration
    print("1. Testing get_model_config() with existing model:")
    model_config = config.get_model_config('lightonocr-2-1b')
    if model_config:
        print(f"   ✓ Retrieved model configuration:")
        print(f"      Model ID: {model_config.model_id}")
        print(f"      Provider: {model_config.provider}")
        print(f"      Name: {model_config.name}")
        print(f"      Base URL: {model_config.base_url}")
        print(f"      Max Tokens: {model_config.max_tokens}")
        print(f"      Temperature: {model_config.temperature}")
        print(f"      Top P: {model_config.top_p}")
    else:
        print("   ✗ Failed to retrieve model configuration")
    print()
    
    # Test 2: Get non-existent model configuration
    print("2. Testing get_model_config() with non-existent model:")
    model_config = config.get_model_config('nonexistent-model')
    if model_config is None:
        print("   ✓ Correctly returned None for non-existent model")
    else:
        print("   ✗ Should have returned None")
    print()
    
    # Test 3: Get all available models
    print("3. Testing get_available_models():")
    available_models = config.get_available_models()
    print(f"   ✓ Found {len(available_models)} available models:")
    for model_id in available_models:
        print(f"      - {model_id}")
    print()
    
    # Test 4: Verify all models can be retrieved
    print("4. Testing that all available models can be retrieved:")
    all_retrievable = True
    for model_id in available_models:
        model_config = config.get_model_config(model_id)
        if model_config is None:
            print(f"   ✗ Failed to retrieve model: {model_id}")
            all_retrievable = False
        else:
            print(f"   ✓ {model_id}: {model_config.name}")
    
    if all_retrievable:
        print("   ✓ All models successfully retrieved")
    print()
    
    # Test 5: Verify base URL resolution from provider
    print("5. Testing base URL resolution from provider:")
    for model_id in available_models:
        model_config = config.get_model_config(model_id)
        provider_config = config.api_providers.get(model_config.provider)
        expected_base_url = provider_config.get('base_url')
        
        if model_config.base_url == expected_base_url:
            print(f"   ✓ {model_id}: Base URL correctly resolved to {model_config.base_url}")
        else:
            print(f"   ✗ {model_id}: Base URL mismatch")
    print()
    
    # Test 6: Verify default model exists
    print("6. Testing default model configuration:")
    default_model_id = config.default_model
    print(f"   Default model ID: {default_model_id}")
    
    default_model_config = config.get_model_config(default_model_id)
    if default_model_config:
        print(f"   ✓ Default model exists: {default_model_config.name}")
    else:
        print(f"   ✗ Default model not found in configuration")
    print()
    
    # Test 7: Verify ModelConfig dataclass fields
    print("7. Testing ModelConfig dataclass structure:")
    model_config = config.get_model_config('lightonocr-2-1b')
    required_fields = ['model_id', 'provider', 'name', 'base_url', 'max_tokens', 'temperature', 'top_p']
    
    all_fields_present = True
    for field in required_fields:
        if hasattr(model_config, field):
            value = getattr(model_config, field)
            print(f"   ✓ {field}: {value}")
        else:
            print(f"   ✗ Missing field: {field}")
            all_fields_present = False
    
    if all_fields_present:
        print("   ✓ All required fields present in ModelConfig")
    print()
    
    print("=" * 70)
    print("Model configuration tests completed!")
    print("=" * 70)


if __name__ == '__main__':
    main()
