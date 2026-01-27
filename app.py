"""
OCR Web UI - Flask Backend
===========================
Flask application that provides a web interface for OCR processing
using LightOnOCR-2-1B via LM Studio.

This backend wraps the existing OCR functionality and provides:
- File upload handling with validation
- OCR processing endpoints
- CORS support for local development
- Error handling and status reporting
"""

import os
from pathlib import Path
from typing import Optional, Tuple

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import requests

# LM Studio configuration
LM_STUDIO_BASE_URL = "http://localhost:1234"
MODEL_ID = "lightonocr-2-1b"

# ============================================================================
# CONFIGURATION
# ============================================================================

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Enable CORS for local development
CORS(app)

# File upload configuration
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'pdf'}

# Model configuration
MODELS = {
    'lightonocr-2-1b': {
        'model_id': 'lightonocr-2-1b',
        'base_url': LM_STUDIO_BASE_URL,
        'name': 'LightOnOCR-2-1B'
    },
    'deepseek-ocr': {
        'model_id': 'deepseek-ocr',
        'base_url': LM_STUDIO_BASE_URL,
        'name': 'DeepSeek OCR'
    },
    'nanonets-ocr2-3b': {
        'model_id': 'nanonets-ocr2-3b',
        'base_url': LM_STUDIO_BASE_URL,
        'name': 'Nanonets OCR2-3B'
    }
}

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def check_server_status() -> dict:
    """
    Check if LM Studio server is running and available.
    
    Returns:
        Dictionary with status information
    """
    try:
        response = requests.get(f"{LM_STUDIO_BASE_URL}/v1/models", timeout=5)
        response.raise_for_status()
        models = response.json()
        return {
            'status': 'running',
            'message': 'Server is running',
            'models': models.get('data', [])
        }
    except requests.exceptions.RequestException as e:
        return {
            'status': 'not_running',
            'message': f'Server is not accessible: {str(e)}',
            'models': []
        }


def allowed_file(filename: str) -> bool:
    """
    Check if the file extension is allowed.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        True if file extension is allowed, False otherwise
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def get_file_type(filename: str) -> Optional[str]:
    """
    Get the file type from filename.
    
    Args:
        filename: Name of the file
        
    Returns:
        File type ('image' or 'pdf') or None if invalid
    """
    if not '.' in filename:
        return None
    
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in {'png', 'jpg', 'jpeg'}:
        return 'image'
    elif ext == 'pdf':
        return 'pdf'
    return None


def process_ocr(file_path: str, file_type: str, model_id: str = 'lightonocr-2-1b', process_all_pages: bool = False) -> Tuple[bool, str, Optional[str]]:
    """
    Process OCR on the uploaded file using the specified model.
    
    Args:
        file_path: Path to the uploaded file
        file_type: Type of file ('image' or 'pdf')
        model_id: ID of the model to use
        process_all_pages: If True, process all pages of PDF (default: False, only first page)
        
    Returns:
        Tuple of (success, text_or_error_or_dict, error_type)
    """
    # Validate model
    if model_id not in MODELS:
        return False, f"Invalid model: {model_id}", "invalid_model"
    
    model_config = MODELS[model_id]
    
    try:
        if file_type == 'image':
            text = ocr_image_with_model(file_path, model_config)
            return True, text, None
        elif file_type == 'pdf':
            if process_all_pages:
                # Process all pages of PDF
                result = ocr_pdf_all_pages_with_model(file_path, model_config)
                return True, result, None
            else:
                # Process only first page of PDF
                text = ocr_pdf_page_with_model(file_path, page_number=0, model_config=model_config)
                return True, text, None
        else:
            return False, "Invalid file type", "invalid_file"
    
    # Handle specific exceptions first (most specific to least specific)
    except requests.exceptions.HTTPError as e:
        # Handle HTTP errors from LM Studio API (4xx, 5xx responses)
        status_code = e.response.status_code if hasattr(e, 'response') and e.response else 'unknown'
        return False, f"LM Studio API error (status {status_code}): {str(e)}", "processing_error"
    except requests.exceptions.ConnectionError:
        return False, f"LM Studio server is not running. Please start the server at {model_config['base_url']}", "connection_error"
    except requests.exceptions.Timeout:
        return False, "Request to LM Studio timed out. The server may be overloaded or not responding.", "connection_error"
    except requests.exceptions.RequestException as e:
        # Catch other requests-related errors (network issues, DNS failures, etc.)
        return False, f"Failed to connect to LM Studio: {str(e)}", "connection_error"
    except ImportError as e:
        # Handle missing dependencies (e.g., pypdfium2 for PDF processing)
        return False, f"Missing required dependency: {str(e)}. Please install required packages.", "processing_error"
    except IOError as e:
        # Handle file reading errors (corrupted files, permission issues)
        return False, f"Failed to read file: {str(e)}. The file may be corrupted or inaccessible.", "processing_error"
    except ValueError as e:
        # Handle invalid data errors (e.g., invalid image format, corrupted base64)
        return False, f"Invalid file format: {str(e)}. The file may be corrupted or in an unsupported format.", "processing_error"
    except KeyError as e:
        # Handle missing fields in API response
        return False, f"Invalid API response: Missing expected field {str(e)}. The LM Studio API may have returned an unexpected format.", "processing_error"
    except Exception as e:
        # Catch any other unexpected errors
        return False, f"OCR processing failed: {str(e)}", "processing_error"


def ocr_image_with_model(image_path: str, model_config: dict) -> str:
    """
    Perform OCR on an image using the specified model configuration.
    
    Args:
        image_path: Path to the image file
        model_config: Model configuration dictionary
        
    Returns:
        Extracted text from the image
    """
    import base64
    from PIL import Image
    
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
    endpoint = f"{model_config['base_url']}/v1/chat/completions"
    payload = {
        "model": model_config['model_id'],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 4096,
        "temperature": 0.2,
        "top_p": 0.9,
    }
    
    # Make request
    response = requests.post(endpoint, json=payload)
    response.raise_for_status()
    
    result = response.json()
    return result["choices"][0]["message"]["content"]


def ocr_pdf_page_with_model(pdf_path: str, page_number: int, model_config: dict) -> str:
    """
    Perform OCR on a PDF page using the specified model configuration.
    
    Args:
        pdf_path: Path to the PDF file
        page_number: Page index (0-based)
        model_config: Model configuration dictionary
        
    Returns:
        Extracted text from the PDF page
    """
    try:
        import pypdfium2 as pdfium
    except ImportError:
        raise ImportError("Please install pypdfium2: pip install pypdfium2")
    
    import base64
    import io
    from PIL import Image
    
    # Open PDF and render page
    pdf = pdfium.PdfDocument(pdf_path)
    page = pdf[page_number]
    
    # Render at 200 DPI
    scale = 200 / 72
    pil_image = page.render(scale=scale).to_pil()
    
    # Convert PIL image to base64
    buffer = io.BytesIO()
    pil_image.save(buffer, format='PNG')
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # Build API request
    endpoint = f"{model_config['base_url']}/v1/chat/completions"
    payload = {
        "model": model_config['model_id'],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 4096,
        "temperature": 0.2,
        "top_p": 0.9,
    }
    
    # Make request
    response = requests.post(endpoint, json=payload)
    response.raise_for_status()
    
    result = response.json()
    return result["choices"][0]["message"]["content"]


def ocr_pdf_all_pages_with_model(pdf_path: str, model_config: dict) -> dict:
    """
    Perform OCR on all pages of a PDF using the specified model configuration.
    
    Args:
        pdf_path: Path to the PDF file
        model_config: Model configuration dictionary
        
    Returns:
        Dictionary with 'text' (combined text from all pages) and 'pages' (page count)
    """
    try:
        import pypdfium2 as pdfium
    except ImportError:
        raise ImportError("Please install pypdfium2: pip install pypdfium2")
    
    # Open PDF and get page count
    pdf = pdfium.PdfDocument(pdf_path)
    page_count = len(pdf)
    
    # Process each page
    all_text = []
    for page_num in range(page_count):
        page_text = ocr_pdf_page_with_model(pdf_path, page_num, model_config)
        all_text.append(f"--- Page {page_num + 1} ---\n{page_text}")
    
    # Combine all pages
    combined_text = "\n\n".join(all_text)
    
    return {
        'text': combined_text,
        'pages': page_count
    }


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory('.', 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files from the root directory."""
    return send_from_directory('.', filename)


@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint.
    Returns server status and LM Studio connection status.
    """
    lm_studio_status = check_server_status()
    
    return jsonify({
        'status': 'running',
        'lm_studio': lm_studio_status
    })


@app.route('/ocr', methods=['POST'])
def ocr():
    """
    OCR endpoint that accepts file uploads and returns extracted text.
    
    Request:
        multipart/form-data with 'file' field, optional 'model' field, and optional 'process_all_pages' field
        
    Response:
        JSON with success status, extracted text, or error message
    """
    # Check if file is present in request
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'No file provided',
            'error_type': 'invalid_file'
        }), 400
    
    file = request.files['file']
    
    # Check if file was selected
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'No file selected',
            'error_type': 'invalid_file'
        }), 400
    
    # Validate file type
    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'error': f'Invalid file type. Allowed types: {", ".join(app.config["ALLOWED_EXTENSIONS"])}',
            'error_type': 'invalid_file'
        }), 400
    
    # Get model selection (default to lightonocr-2-1b)
    model_id = request.form.get('model', 'lightonocr-2-1b')
    
    # Get process_all_pages flag (default to False for backward compatibility)
    process_all_pages = request.form.get('process_all_pages', 'false').lower() == 'true'
    
    # Validate model
    if model_id not in MODELS:
        return jsonify({
            'success': False,
            'error': f'Invalid model: {model_id}. Available models: {", ".join(MODELS.keys())}',
            'error_type': 'invalid_model'
        }), 400
    
    # Save file securely
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    try:
        # Determine file type and process
        file_type = get_file_type(filename)
        success, result, error_type = process_ocr(file_path, file_type, model_id, process_all_pages)
        
        if success:
            response_data = {
                'success': True,
                'text': result['text'] if isinstance(result, dict) else result,
                'filename': filename,
                'model': model_id
            }
            
            # Add page count if available
            if isinstance(result, dict) and 'pages' in result:
                response_data['pages'] = result['pages']
            
            return jsonify(response_data)
        else:
            return jsonify({
                'success': False,
                'error': result,
                'error_type': error_type,
                'filename': filename,
                'model': model_id
            }), 500
            
    finally:
        # Clean up uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error."""
    return jsonify({
        'success': False,
        'error': f'File too large. Maximum size is {app.config["MAX_CONTENT_LENGTH"] // (1024*1024)}MB',
        'error_type': 'file_too_large'
    }), 413


@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors."""
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'error_type': 'server_error'
    }), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Check LM Studio status on startup
    print("=" * 60)
    print("OCR Web UI - Flask Backend")
    print("=" * 60)
    
    status = check_server_status()
    print(f"LM Studio Status: {status['status']}")
    print(f"Message: {status['message']}")
    
    if status['status'] == 'running':
        print(f"Model ID: {MODEL_ID}")
        print(f"API URL: {LM_STUDIO_BASE_URL}")
        print("✅ Ready to process OCR requests!")
    else:
        print("⚠️  Warning: LM Studio is not running!")
        print("   The server will start, but OCR requests will fail.")
        print("   Please start LM Studio and load the lightonocr-2-1b model.")
    
    print("\n" + "=" * 60)
    print("Starting Flask server...")
    print("Access the web UI at: http://localhost:5001")
    print("=" * 60 + "\n")
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5001)
