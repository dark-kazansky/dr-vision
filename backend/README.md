# OCR Web UI - FastAPI Backend

A modern, modular FastAPI backend for OCR processing with multiple model support.

## Features

- **Multiple OCR Models**: Support for lightonocr-2-1b, deepseek-ocr, and nanonets-ocr2-3b
- **Flexible Configuration**: YAML-based configuration with environment variable overrides
- **Image & PDF Support**: Process PNG, JPG, JPEG, and PDF files
- **Multi-page PDF**: Process single or all pages of PDF documents
- **Type Safety**: Pydantic models for request/response validation
- **Automatic API Docs**: OpenAPI documentation at `/docs`
- **CORS Support**: Configurable cross-origin resource sharing
- **Error Handling**: Comprehensive error handling with specific error types

## Project Structure

```
backend/
├── config/
│   └── config.yaml              # Main configuration file
├── src/
│   ├── __init__.py
│   ├── config.py                # Configuration loader and validator
│   ├── models.py                # Pydantic request/response models
│   ├── ocr_processor.py         # OCR processing logic
│   ├── routes.py                # FastAPI route handlers
│   └── utils.py                 # Utility functions
├── main.py                      # FastAPI application entry point
└── requirements.txt             # Python dependencies
```

## Installation

### Prerequisites

- Python 3.9 or higher
- LM Studio running with an OCR model loaded (for DeepSeek-OCR and Nanonets-OCR2-3B)
- LightOnOCR-2-1B is served via vLLM at aimsb.theworkpc.com:8081 (production API)

### Setup

1. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure the application:**
   
   Edit `config/config.yaml` to customize settings:
   - API provider URLs (LM Studio for local models, vLLM for LightOnOCR)
   - Model configurations
   - Server settings (host, port, CORS)
   - Upload constraints (max size, allowed extensions)

3. **Start OCR Services:**
   
   - **LightOnOCR-2-1B**: Served via vLLM at `http://aimsb.theworkpc.com:8081` (production API, no local setup needed)
   - **Other models**: Ensure LM Studio is running at `http://localhost:1234` (or your configured URL) with the desired OCR model loaded

## Configuration

### Configuration File (`config/config.yaml`)

The configuration file contains all application settings:

#### API Providers
```yaml
api_providers:
  lm_studio:
    base_url: "http://localhost:1234"
    timeout: 30
  
  lightonocr_api:
    # Production LightOnOCR API server (vLLM-based)
    base_url: "http://aimsb.theworkpc.com:8081"
    timeout: 300
```

#### Models
```yaml
models:
  lightonocr-2-1b:
    model_id: "lightonocr-2-1b"
    provider: "lightonocr_api"  # Uses vLLM production API
    name: "LightOnOCR-2-1B (Production)"
    max_tokens: 4096
    temperature: 0.2
    top_p: 0.9
  
  deepseek-ocr:
    model_id: "deepseek-ocr"
    provider: "lm_studio"  # Uses local LM Studio
    name: "DeepSeek OCR"
    max_tokens: 4096
    temperature: 0.2
    top_p: 0.9
```

#### FastAPI Settings
```yaml
fastapi:
  debug: true
  host: "0.0.0.0"
  port: 8000
  cors_origins:
    - "http://localhost:3000"
```

#### Upload Settings
```yaml
upload:
  folder: "uploads"
  max_size_mb: 10
  allowed_extensions:
    - png
    - jpg
    - jpeg
    - pdf
```

### Environment Variables

Override configuration values using environment variables:

- `LM_STUDIO_BASE_URL`: Override LM Studio base URL
- `DEFAULT_MODEL_ID`: Override default model
- `UPLOAD_FOLDER`: Override upload directory
- `MAX_FILE_SIZE_MB`: Override maximum file size

**Example:**
```bash
export LM_STUDIO_BASE_URL=http://remote-server:1234
export DEFAULT_MODEL_ID=deepseek-ocr
python main.py
```

## Running the Server

### Development Mode

```bash
cd backend
python main.py
```

The server will start at `http://0.0.0.0:8000` (or your configured host/port).

### Production Mode

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

For production, consider using:
- Gunicorn with Uvicorn workers
- Docker container
- Process manager (systemd, supervisor)

## API Endpoints

### POST /ocr

Process OCR on uploaded file.

**Request:**
- Content-Type: `multipart/form-data`
- Fields:
  - `file`: File to process (required)
  - `model_id`: Model ID to use (required)
  - `process_all_pages`: Process all PDF pages (optional, default: false)
  - `tier`: Processing tier - Rapid/Normal/Advance (optional, default: Normal)

**Response:**
```json
{
  "success": true,
  "text": "Extracted text...",
  "filename": "document.pdf",
  "model": "lightonocr-2-1b",
  "pages": 1
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error message",
  "error_type": "connection_error",
  "filename": "document.pdf",
  "model": "lightonocr-2-1b"
}
```

**Error Types:**
- `invalid_model`: Model ID not found
- `invalid_file`: File type not supported or file invalid
- `connection_error`: Cannot connect to API provider
- `processing_error`: Error during OCR processing
- `file_too_large`: File exceeds size limit

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "server_running": true,
  "available_models": ["lightonocr-2-1b", "deepseek-ocr", "nanonets-ocr2-3b"]
}
```

### GET /docs

Interactive API documentation (Swagger UI).

### GET /redoc

Alternative API documentation (ReDoc).

## Testing

### Manual Testing

Use the provided test scripts:

```bash
# Test configuration loading
python demo_config.py

# Test Pydantic models
python test_models_demo.py

# Test environment variable overrides
python test_env_overrides.py

# Test configuration validation
python test_validation.py

# Test model configuration retrieval
python test_model_config.py
```

### API Testing

Use curl or httpx to test endpoints:

```bash
# Health check
curl http://localhost:8000/health

# OCR processing
curl -X POST http://localhost:8000/ocr \
  -F "file=@document.pdf" \
  -F "model_id=lightonocr-2-1b" \
  -F "process_all_pages=false"
```

## Adding New Models

1. **Add model configuration to `config/config.yaml`:**
   ```yaml
   models:
     my-new-model:
       model_id: "my-new-model"
       provider: "lm_studio"
       name: "My New Model"
       max_tokens: 4096
       temperature: 0.2
       top_p: 0.9
   ```

2. **Restart the server** - No code changes required!

3. **Verify model is available:**
   ```bash
   curl http://localhost:8000/health
   ```

## Adding New API Providers

1. **Add provider configuration to `config/config.yaml`:**
   ```yaml
   api_providers:
     my_provider:
       base_url: "http://my-provider:8080"
       timeout: 30
   ```

2. **Update model configurations** to use the new provider:
   ```yaml
   models:
     my-model:
       provider: "my_provider"
       # ... other settings
   ```

3. **Restart the server** - No code changes required!

## Troubleshooting

### Configuration Errors

If the server fails to start with configuration errors:

1. Check `config/config.yaml` syntax (valid YAML)
2. Ensure all required sections are present
3. Verify model provider references exist
4. Check numeric values are in valid ranges

Run validation manually:
```bash
python demo_config.py
```

### Connection Errors

If OCR requests fail with connection errors:

1. Verify LM Studio is running
2. Check the base URL in configuration
3. Ensure the model is loaded in LM Studio
4. Test the connection:
   ```bash
   curl http://localhost:1234/v1/models
   ```

### File Upload Errors

If file uploads fail:

1. Check file size is under the limit (default: 10MB)
2. Verify file extension is allowed (png, jpg, jpeg, pdf)
3. Ensure upload folder exists and is writable
4. Check disk space

### Import Errors

If you get import errors:

1. Ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Verify Python version (3.9+):
   ```bash
   python --version
   ```

## Development

### Code Structure

- **config.py**: Configuration management with validation
- **models.py**: Pydantic models for type safety
- **ocr_processor.py**: Core OCR logic (framework-independent)
- **utils.py**: Reusable utility functions
- **routes.py**: FastAPI route handlers
- **main.py**: Application initialization and startup

### Design Principles

1. **Separation of Concerns**: Business logic separate from web framework
2. **Configuration-Driven**: All settings externalized to YAML
3. **Type Safety**: Pydantic models for validation
4. **Error Handling**: Comprehensive error handling with specific types
5. **Testability**: Modules designed for easy testing

## Migration from Flask

This FastAPI backend replaces the original Flask `app.py`. Key differences:

### Advantages

- **Automatic API Documentation**: OpenAPI docs at `/docs`
- **Type Safety**: Pydantic validation catches errors early
- **Async Support**: Better performance for I/O operations
- **Modern Python**: Uses Python 3.9+ features
- **Modular Design**: Easier to maintain and extend

### API Compatibility

The FastAPI backend maintains API compatibility with the original Flask version:

- Same endpoints (`/ocr`, `/health`)
- Same request/response formats
- Same error handling behavior
- Same file type support

### Configuration Changes

- Configuration moved from hardcoded values to `config.yaml`
- Environment variables supported for deployment flexibility
- Validation ensures configuration correctness

## License

[Your License Here]

## Support

For issues or questions:
- Check the troubleshooting section
- Review configuration documentation
- Test with provided scripts
- Check LM Studio connection

---

**Version:** 2.0.0  
**Last Updated:** January 27, 2026
