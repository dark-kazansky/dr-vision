"""
Utility functions for the OCR Web UI application.

This module provides reusable utility functions for:
- File validation and type detection
- Server health checks
- Secure file upload handling

Requirements: 3.2, 5.2, 8.2
"""

import os
import secrets
from pathlib import Path
from typing import Optional, Set
import requests
from fastapi import HTTPException, UploadFile


def allowed_file(filename: str, allowed_extensions: Set[str]) -> bool:
    """
    Check if file extension is allowed.
    
    Args:
        filename: Name of the file to check
        allowed_extensions: Set of allowed file extensions (without dots)
        
    Returns:
        True if file extension is in allowed_extensions, False otherwise
        
    Examples:
        >>> allowed_file("document.pdf", {"pdf", "png"})
        True
        >>> allowed_file("script.exe", {"pdf", "png"})
        False
        >>> allowed_file("image.PNG", {"pdf", "png"})
        True
    """
    if not filename or '.' not in filename:
        return False
    
    # Get extension without the dot and convert to lowercase
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in allowed_extensions


def get_file_type(filename: str) -> Optional[str]:
    """
    Determine file type from extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        'image' for image files (png, jpg, jpeg)
        'pdf' for PDF files
        None for unsupported file types
        
    Examples:
        >>> get_file_type("photo.jpg")
        'image'
        >>> get_file_type("document.pdf")
        'pdf'
        >>> get_file_type("script.exe")
        None
    """
    if not filename or '.' not in filename:
        return None
    
    # Get extension without the dot and convert to lowercase
    extension = filename.rsplit('.', 1)[1].lower()
    
    # Map extensions to file types
    if extension in {'png', 'jpg', 'jpeg'}:
        return 'image'
    elif extension == 'pdf':
        return 'pdf'
    else:
        return None


def check_server_status(base_url: str, timeout: int = 5) -> dict:
    """
    Check if API server is running.
    
    Args:
        base_url: Base URL of the API server (e.g., "http://localhost:1234")
        timeout: Request timeout in seconds (default: 5)
        
    Returns:
        Dictionary with:
        - 'running': bool indicating if server is accessible
        - 'url': str with the base URL checked
        - 'error': Optional str with error message if server is not running
        
    Examples:
        >>> check_server_status("http://localhost:1234")
        {'running': True, 'url': 'http://localhost:1234', 'error': None}
        >>> check_server_status("http://localhost:9999")
        {'running': False, 'url': 'http://localhost:9999', 'error': '...'}
    """
    try:
        # Try to connect to the server with a simple GET request
        # Most API servers respond to root or have a health endpoint
        response = requests.get(base_url, timeout=timeout)
        
        # Consider any response (even errors) as "server is running"
        # because it means we could connect to it
        return {
            'running': True,
            'url': base_url,
            'error': None
        }
    except requests.exceptions.ConnectionError as e:
        return {
            'running': False,
            'url': base_url,
            'error': f'Connection error: {str(e)}'
        }
    except requests.exceptions.Timeout as e:
        return {
            'running': False,
            'url': base_url,
            'error': f'Timeout error: {str(e)}'
        }
    except Exception as e:
        return {
            'running': False,
            'url': base_url,
            'error': f'Unexpected error: {str(e)}'
        }


def strip_code_blocks(content: str) -> str:
    """
    Remove markdown code fences from LLM response content.

    Handles leading ```json or ``` fences and trailing ``` fences.
    Returns the inner content stripped of surrounding whitespace.

    Args:
        content: Raw LLM response that may be wrapped in code fences

    Returns:
        Content with code fences removed and whitespace stripped

    Examples:
        >>> strip_code_blocks('```json\\n{"a": 1}\\n```')
        '{"a": 1}'
        >>> strip_code_blocks('```\\n{"a": 1}\\n```')
        '{"a": 1}'
        >>> strip_code_blocks('{"a": 1}')
        '{"a": 1}'
    """
    if content.startswith('```'):
        lines = content.split('\n')
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        content = '\n'.join(lines).strip()
    return content


def validate_file_path(filename: str, base_directory: str) -> str:
    """
    Validate that a filename resolves to a path within the base directory.

    Rejects path traversal sequences (..) and absolute paths to prevent
    unauthorized file access outside the expected data directory.

    Args:
        filename: The filename to validate
        base_directory: The directory the resolved path must stay within

    Returns:
        The resolved full path as a string

    Raises:
        HTTPException(400): If the filename contains traversal sequences,
            is an absolute path, or resolves outside base_directory
    """
    # Reject absolute paths
    if os.path.isabs(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Reject path traversal sequences
    if ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Resolve the full path and verify it stays within base_directory
    base = os.path.realpath(base_directory)
    full_path = os.path.realpath(os.path.join(base, filename))

    if not full_path.startswith(base + os.sep) and full_path != base:
        raise HTTPException(status_code=400, detail="Invalid filename")

    return full_path


async def secure_save_file(file: UploadFile, upload_folder: str) -> str:
    """
    Securely save uploaded file and return path.
    
    This function:
    - Creates upload folder if it doesn't exist
    - Generates a secure random filename to prevent path traversal attacks
    - Preserves the original file extension
    - Saves the file to the upload folder
    - Returns the full path to the saved file
    
    Args:
        file: FastAPI UploadFile object
        upload_folder: Directory where files should be saved
        
    Returns:
        Full path to the saved file
        
    Raises:
        ValueError: If filename is invalid or missing
        IOError: If file cannot be saved
        
    Examples:
        >>> await secure_save_file(upload_file, "uploads")
        'uploads/a3f2b1c4d5e6f7g8_document.pdf'
    """
    if not file.filename:
        raise ValueError("File must have a filename")
    
    # Create upload folder if it doesn't exist
    upload_path = Path(upload_folder)
    upload_path.mkdir(parents=True, exist_ok=True)
    
    # Get the original file extension
    original_filename = file.filename
    if '.' in original_filename:
        extension = original_filename.rsplit('.', 1)[1].lower()
        # Sanitize extension to prevent path traversal
        extension = extension.replace('/', '').replace('\\', '')
    else:
        extension = ''
    
    # Generate a secure random filename
    # Use secrets module for cryptographically strong random values
    random_hex = secrets.token_hex(16)
    
    # Create secure filename: random_hex + original_name (sanitized)
    # Sanitize original filename to remove path components
    safe_original = original_filename.replace('/', '_').replace('\\', '_')
    if extension:
        secure_filename = f"{random_hex}_{safe_original}"
    else:
        secure_filename = f"{random_hex}_{safe_original}"
    
    # Full path to save the file
    file_path = upload_path / secure_filename
    
    try:
        # Read and save file content
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Return the full path as a string
        return str(file_path)
    except Exception as e:
        # Clean up partial file if save failed
        if file_path.exists():
            file_path.unlink()
        raise IOError(f"Failed to save file: {str(e)}")
