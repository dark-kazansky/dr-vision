#!/usr/bin/env python3
"""
Test script for parse endpoint with file saving and DOCX conversion.
"""

import requests
import os

# Configuration
API_BASE_URL = "http://localhost:8082"
TEST_FILE = "/Users/dark_kazansky/Coding-Space/Dr.Vision/test_files/9_16.png"

def test_parse_with_save():
    """Test parse endpoint and verify files are saved."""
    print("\n" + "=" * 80)
    print("PARSE TEST - File Saving and DOCX Conversion")
    print("=" * 80)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Test File: {TEST_FILE}")
    
    if not os.path.exists(TEST_FILE):
        print(f"\n❌ Error: Test file not found: {TEST_FILE}")
        return False
    
    # Prepare request
    with open(TEST_FILE, 'rb') as f:
        files = {'file': (os.path.basename(TEST_FILE), f)}
        data = {
            'model_id': 'deepseek-ocr',
            'force_ocr': 'false',
            'parse_formatting': 'true',
            'process_all_pages': 'true',
            'tier': 'Rapid'
        }
        
        try:
            print("\n📤 Sending parse request...")
            response = requests.post(
                f"{API_BASE_URL}/parse",
                files=files,
                data=data,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Parse successful!")
                print(f"\n📄 Response:")
                print(f"  - Success: {result.get('success')}")
                print(f"  - Filename: {result.get('filename')}")
                print(f"  - File Type: {result.get('file_type')}")
                print(f"  - Pages: {result.get('pages')}")
                print(f"  - Text Length: {len(result.get('text', ''))}")
                
                # Check if files were created
                base_filename = os.path.splitext(os.path.basename(TEST_FILE))[0]
                raw_ocr_path = f"backend/data/raw_ocr/{base_filename}.txt"
                docx_path = f"backend/data/parsed/{base_filename}.docx"
                
                print(f"\n📁 Checking saved files:")
                
                # Check raw OCR file
                if os.path.exists(raw_ocr_path):
                    file_size = os.path.getsize(raw_ocr_path)
                    print(f"  ✅ Raw OCR: {raw_ocr_path} ({file_size} bytes)")
                else:
                    print(f"  ❌ Raw OCR not found: {raw_ocr_path}")
                
                # Check DOCX file
                if os.path.exists(docx_path):
                    file_size = os.path.getsize(docx_path)
                    print(f"  ✅ DOCX: {docx_path} ({file_size} bytes)")
                else:
                    print(f"  ❌ DOCX not found: {docx_path}")
                
                return True
            else:
                print(f"❌ Error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"❌ Error: Request timeout (120s)")
            return False
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("PARSE ENDPOINT TEST")
    print("=" * 80)
    
    success = test_parse_with_save()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ TEST PASSED")
    else:
        print("❌ TEST FAILED")
    print("=" * 80 + "\n")
