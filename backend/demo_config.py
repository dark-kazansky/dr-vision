#!/usr/bin/env python3
"""
Demonstration script for config.py module.

This script shows how to use the Config class to load and access configuration.
"""

import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config import Config, ConfigurationError


def main():
    print("=" * 70)
    print("OCR Web UI Configuration Loader Demo")
    print("=" * 70)
    print()
    
    try:
        # Load configuration
        print("Loading configuration from backend/config/config.yaml...")
        config = Config.load('backend/config/config.yaml')
        print("✓ Configuration loaded successfully\n")
        
        # Validate configuration
        print("Validating configuration...")
        errors = config.validate()
        if errors:
            print("✗ Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("✓ Configuration is valid\n")
        
        # Display API providers
        print("API Providers:")
        for provider_name, provider_config in config.api_providers.items():
            print(f"  - {provider_name}: {provider_config.get('base_url')}")
        print()
        
        # Display available models
        print("Available Models:")
        for model_id in config.get_available_models():
            model_config = config.get_model_config(model_id)
            print(f"  - {model_id}")
            print(f"    Name: {model_config.name}")
            print(f"    Provider: {model_config.provider}")
            print(f"    Base URL: {model_config.base_url}")
            print(f"    Max Tokens: {model_config.max_tokens}")
            print(f"    Temperature: {model_config.temperature}")
        print()
        
        # Display default model
        print(f"Default Model: {config.default_model}")
        print()
        
        # Display FastAPI configuration
        print("FastAPI Configuration:")
        fastapi = config.fastapi_config
        print(f"  Host: {fastapi.get('host')}")
        print(f"  Port: {fastapi.get('port')}")
        print(f"  Debug: {fastapi.get('debug')}")
        print(f"  CORS Origins: {', '.join(fastapi.get('cors_origins', []))}")
        print()
        
        # Display upload configuration
        print("Upload Configuration:")
        upload = config.upload_config
        print(f"  Folder: {upload.get('folder')}")
        print(f"  Max Size: {upload.get('max_size_mb')} MB")
        print(f"  Allowed Extensions: {', '.join(upload.get('allowed_extensions', []))}")
        print()
        
        # Display PDF configuration
        print("PDF Configuration:")
        pdf = config.pdf_config
        print(f"  Render DPI: {pdf.get('render_dpi')}")
        print(f"  Process All Pages by Default: {pdf.get('default_process_all_pages')}")
        print()
        
        print("=" * 70)
        print("Environment Variable Overrides:")
        print("=" * 70)
        print("You can override configuration values using these environment variables:")
        print("  - LM_STUDIO_BASE_URL: Override LM Studio base URL")
        print("  - DEFAULT_MODEL_ID: Override default model")
        print("  - UPLOAD_FOLDER: Override upload directory")
        print("  - MAX_FILE_SIZE_MB: Override maximum file size")
        print()
        print("Example:")
        print("  export LM_STUDIO_BASE_URL=http://remote-server:1234")
        print("  python backend/demo_config.py")
        print()
        
    except ConfigurationError as e:
        print(f"✗ Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
