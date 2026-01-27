#!/usr/bin/env python3
"""
Test script for configuration validation.

This script tests various invalid configurations to ensure validation works.
"""

import sys
import tempfile
import os
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config import Config, ConfigurationError


def test_missing_file():
    """Test loading non-existent configuration file."""
    print("1. Testing missing configuration file:")
    try:
        config = Config.load('nonexistent.yaml')
        print("   ✗ Should have raised ConfigurationError")
        return False
    except ConfigurationError as e:
        print(f"   ✓ Correctly raised error: {e}")
        return True


def test_invalid_yaml():
    """Test loading file with invalid YAML syntax."""
    print("\n2. Testing invalid YAML syntax:")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("invalid: yaml: syntax: here\n  bad indentation")
        temp_file = f.name
    
    try:
        config = Config.load(temp_file)
        print("   ✗ Should have raised ConfigurationError")
        return False
    except ConfigurationError as e:
        print(f"   ✓ Correctly raised error: Invalid YAML syntax")
        return True
    finally:
        os.unlink(temp_file)


def test_missing_required_sections():
    """Test configuration missing required sections."""
    print("\n3. Testing missing required sections:")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("# Empty config with only one section\nmodels: {}\n")
        temp_file = f.name
    
    try:
        config = Config.load(temp_file)
        errors = config.validate()
        if errors:
            print(f"   ✓ Validation found {len(errors)} error(s):")
            for error in errors[:3]:  # Show first 3 errors
                print(f"      - {error}")
            return True
        else:
            print("   ✗ Should have found validation errors")
            return False
    finally:
        os.unlink(temp_file)


def test_invalid_model_config():
    """Test model configuration with missing required fields."""
    print("\n4. Testing invalid model configuration:")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
api_providers:
  lm_studio:
    base_url: "http://localhost:1234"

models:
  test-model:
    # Missing required fields: model_id, provider, name
    max_tokens: 4096

fastapi:
  host: "0.0.0.0"
  port: 8000

upload:
  folder: "uploads"
  max_size_mb: 10
  allowed_extensions: [png, jpg]
""")
        temp_file = f.name
    
    try:
        config = Config.load(temp_file)
        errors = config.validate()
        if errors:
            print(f"   ✓ Validation found {len(errors)} error(s):")
            for error in errors:
                if 'test-model' in error:
                    print(f"      - {error}")
            return True
        else:
            print("   ✗ Should have found validation errors")
            return False
    finally:
        os.unlink(temp_file)


def test_invalid_provider_reference():
    """Test model referencing non-existent provider."""
    print("\n5. Testing model with invalid provider reference:")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
api_providers:
  lm_studio:
    base_url: "http://localhost:1234"

models:
  test-model:
    model_id: "test-model"
    provider: "nonexistent-provider"
    name: "Test Model"

fastapi:
  host: "0.0.0.0"
  port: 8000

upload:
  folder: "uploads"
  max_size_mb: 10
  allowed_extensions: [png, jpg]
""")
        temp_file = f.name
    
    try:
        config = Config.load(temp_file)
        errors = config.validate()
        if errors:
            print(f"   ✓ Validation found error:")
            for error in errors:
                if 'unknown provider' in error.lower():
                    print(f"      - {error}")
            return True
        else:
            print("   ✗ Should have found validation errors")
            return False
    finally:
        os.unlink(temp_file)


def test_invalid_numeric_values():
    """Test configuration with invalid numeric values."""
    print("\n6. Testing invalid numeric values:")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
api_providers:
  lm_studio:
    base_url: "http://localhost:1234"

models:
  test-model:
    model_id: "test-model"
    provider: "lm_studio"
    name: "Test Model"
    max_tokens: -100
    temperature: 5.0
    top_p: 2.0

fastapi:
  host: "0.0.0.0"
  port: 99999

upload:
  folder: "uploads"
  max_size_mb: -5
  allowed_extensions: [png]
""")
        temp_file = f.name
    
    try:
        config = Config.load(temp_file)
        errors = config.validate()
        if errors:
            print(f"   ✓ Validation found {len(errors)} error(s):")
            for error in errors[:5]:  # Show first 5 errors
                print(f"      - {error}")
            return True
        else:
            print("   ✗ Should have found validation errors")
            return False
    finally:
        os.unlink(temp_file)


def test_valid_configuration():
    """Test that valid configuration passes validation."""
    print("\n7. Testing valid configuration:")
    config = Config.load('backend/config/config.yaml')
    errors = config.validate()
    if not errors:
        print("   ✓ Valid configuration passes validation")
        return True
    else:
        print(f"   ✗ Valid configuration failed validation: {errors}")
        return False


def main():
    print("=" * 70)
    print("Configuration Validation Tests")
    print("=" * 70)
    print()
    
    tests = [
        test_missing_file,
        test_invalid_yaml,
        test_missing_required_sections,
        test_invalid_model_config,
        test_invalid_provider_reference,
        test_invalid_numeric_values,
        test_valid_configuration
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"   ✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All validation tests passed!")
    else:
        print("✗ Some tests failed")
    print("=" * 70)
    
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
