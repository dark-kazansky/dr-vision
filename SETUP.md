# OCR Web UI - Setup Guide

## Overview

This is a web-based OCR application that uses LightOnOCR-2-1B via LM Studio to extract text from images and PDF files.

## Prerequisites

1. **LM Studio** - Download and install from [lmstudio.ai](https://lmstudio.ai)
2. **Python 3.8+** - Required for running the Flask backend
3. **LightOnOCR-2-1B Model** - Download via LM Studio:
   - Model: `staghado/LightOnOCR-2-1B-Q4_K_M-GGUF`
   - API Identifier: `lightonocr-2-1b`

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- Flask (web framework)
- Flask-CORS (CORS support)
- requests (HTTP client)
- Pillow (image processing)
- pypdfium2 (PDF processing)
- pytest (testing)

### 2. Start LM Studio Server

1. Open LM Studio
2. Load the `lightonocr-2-1b` model
3. Go to the "Local Server" tab
4. Click "Start Server" (default port: 1234)
5. Verify the server is running at `http://localhost:1234`

### 3. Start the Flask Backend

```bash
python app.py
```

The server will start on `http://localhost:5000`

You should see output like:
```
============================================================
OCR Web UI - Flask Backend
============================================================
LM Studio Status: running
Message: Server is running
Model ID: lightonocr-2-1b
API URL: http://localhost:1234
✅ Ready to process OCR requests!

============================================================
Starting Flask server...
Access the web UI at: http://localhost:5000
============================================================
```

## Usage

### Web Interface

1. Open your browser and navigate to `http://localhost:5000`
2. The web interface will be available (to be implemented in later tasks)

### API Endpoints

#### Health Check
```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "running",
  "lm_studio": {
    "status": "running",
    "message": "Server is running",
    "models": [...]
  }
}
```

#### OCR Processing
```bash
curl -X POST http://localhost:5000/ocr \
  -F "file=@/path/to/image.png"
```

Success Response:
```json
{
  "success": true,
  "text": "Extracted text content...",
  "filename": "image.png"
}
```

Error Response:
```json
{
  "success": false,
  "error": "Error message",
  "error_type": "connection_error|invalid_file|processing_error",
  "filename": "image.png"
}
```

## Configuration

The Flask app can be configured by modifying `app.py`:

- **MAX_CONTENT_LENGTH**: Maximum file upload size (default: 10MB)
- **UPLOAD_FOLDER**: Temporary folder for uploaded files (default: 'uploads')
- **ALLOWED_EXTENSIONS**: Allowed file types (default: png, jpg, jpeg, pdf)
- **LM_STUDIO_BASE_URL**: LM Studio API URL (default: http://localhost:1234)
- **MODEL_ID**: Model identifier (default: lightonocr-2-1b)

## Testing

Run the test suite:

```bash
pytest test_app.py -v
```

This will run unit tests for:
- File validation
- File type detection
- Health endpoint
- OCR endpoint
- Error handling
- Configuration

## Troubleshooting

### LM Studio Not Running

If you see:
```
⚠️  Warning: LM Studio is not running!
```

Solution:
1. Open LM Studio
2. Load the lightonocr-2-1b model
3. Start the local server
4. Verify it's running at http://localhost:1234

### Connection Errors

If OCR requests fail with connection errors:
- Check that LM Studio server is running
- Verify the port is 1234 (default)
- Check firewall settings

### File Upload Errors

If file uploads fail:
- Check file size (must be under 10MB)
- Verify file type (png, jpg, jpeg, pdf only)
- Ensure the uploads folder has write permissions

## Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────┐
│   Flask     │
│   Backend   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Existing   │
│  OCR Code   │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────┐
│ LM Studio   │
│   API       │
│ (port 1234) │
└─────────────┘
```

## Next Steps

Task 1 (current) has set up:
- ✅ Flask application structure
- ✅ File upload handling with validation
- ✅ Wrapper functions around existing OCR code
- ✅ CORS configuration
- ✅ Error handling
- ✅ Unit tests

Upcoming tasks will add:
- Frontend HTML/CSS/JavaScript interface
- File preview functionality
- Results display with copy-to-clipboard
- Property-based tests
- UI polish and styling

## Files

- `app.py` - Main Flask application
- `test_app.py` - Unit tests
- `index.html` - Frontend (placeholder)
- `lightonocr_inference.py` - Existing OCR code
- `requirements.txt` - Python dependencies
- `SETUP.md` - This file

## Requirements Validation

This implementation satisfies the following requirements:

- **6.1**: Uses existing Python functions for OCR processing
- **6.2**: Maintains current base64 encoding implementation
- **6.3**: Maintains current API endpoint (http://localhost:1234)
- **6.4**: Maintains current model ID (lightonocr-2-1b)
- **6.5**: Provides HTTP API endpoint (/ocr) for UI integration
