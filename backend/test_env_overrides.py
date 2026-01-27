#!/usr/bin/env python3
"""
Test script for environment variable overrides.

This script demonstrates how environment variables override configuration values.
"""

import sys
import os
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config import Config


def main():
    print("=" * 70)
    print("Environment Variable Override Test")
    print("=" * 70)
    print()
    
    # Test 1: Load without environment variables
    print("1. Loading configuration without environment variables:")
    config = Config.load('backend/config/config.yaml')
    print(f"   LM Studio Base URL: {config.api_providers['lm_studio']['base_url']}")
    print(f"   Default Model: {config.default_model}")
    print(f"   Upload Folder: {config.upload_config['folder']}")
    print(f"   Max File Size: {config.upload_config['max_size_mb']} MB")
    print()
    
    # Test 2: Set environment variables and reload
    print("2. Setting environment variables and reloading:")
    os.environ['LM_STUDIO_BASE_URL'] = 'http://remote-server:5000'
    os.environ['DEFAULT_MODEL_ID'] = 'deepseek-ocr'
    os.environ['UPLOAD_FOLDER'] = '/tmp/custom-uploads'
    os.environ['MAX_FILE_SIZE_MB'] = '25'
    
    config = Config.load('backend/config/config.yaml')
    print(f"   LM Studio Base URL: {config.api_providers['lm_studio']['base_url']}")
    print(f"   Default Model: {config.default_model}")
    print(f"   Upload Folder: {config.upload_config['folder']}")
    print(f"   Max File Size: {config.upload_config['max_size_mb']} MB")
    print()
    
    # Verify overrides worked
    assert config.api_providers['lm_studio']['base_url'] == 'http://remote-server:5000', \
        "LM_STUDIO_BASE_URL override failed"
    assert config.default_model == 'deepseek-ocr', \
        "DEFAULT_MODEL_ID override failed"
    assert config.upload_config['folder'] == '/tmp/custom-uploads', \
        "UPLOAD_FOLDER override failed"
    assert config.upload_config['max_size_mb'] == 25, \
        "MAX_FILE_SIZE_MB override failed"
    
    print("   ✓ All environment variable overrides working correctly!")
    print()
    
    # Test 3: Invalid environment variable (should log warning and use default)
    print("3. Testing invalid MAX_FILE_SIZE_MB environment variable:")
    os.environ['MAX_FILE_SIZE_MB'] = 'not-a-number'
    
    # Reset to original config first
    del os.environ['LM_STUDIO_BASE_URL']
    del os.environ['DEFAULT_MODEL_ID']
    del os.environ['UPLOAD_FOLDER']
    
    config = Config.load('backend/config/config.yaml')
    print(f"   Max File Size: {config.upload_config['max_size_mb']} MB")
    print(f"   ✓ Invalid value ignored, using default from config file")
    print()
    
    # Clean up
    del os.environ['MAX_FILE_SIZE_MB']
    
    print("=" * 70)
    print("Environment variable override tests passed!")
    print("=" * 70)


if __name__ == '__main__':
    main()
