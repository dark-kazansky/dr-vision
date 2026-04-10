#!/usr/bin/env python3
"""
Test extraction with file saving.
"""

import requests
import os
import json
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8082"
TEST_FILE = "/Users/dark_kazansky/Coding-Space/Dr.Vision/backend/data/uploaded/BCTC.pdf"

# Extraction schema
EXTRACTION_SCHEMA = [
    {
        "name": "company_name",
        "type": "string",
        "description": "Name of the company",
        "required": True
    },
    {
        "name": "tax_code",
        "type": "string",
        "description": "Tax identification number",
        "required": True
    },
    {
        "name": "quarter",
        "type": "string",
        "description": "Tax quarter (e.g., Quý 4 năm 2024)",
        "required": True
    },
    {
        "name": "total_revenue",
        "type": "number",
        "description": "Total revenue amount",
        "required": False
    },
    {
        "name": "vat_amount",
        "type": "number",
        "description": "VAT amount to be paid",
        "required": False
    }
]


def test_extraction():
    """Test extraction with file saving."""
    print("=" * 80)
    print("EXTRACTION TEST WITH FILE SAVING")
    print("=" * 80)
    
    # Check if test file exists
    if not os.path.exists(TEST_FILE):
        print(f"❌ Test file not found: {TEST_FILE}")
        return
    
    print(f"✅ Test file: {TEST_FILE}")
    print(f"📋 Schema fields: {len(EXTRACTION_SCHEMA)}")
    
    # Prepare form data
    with open(TEST_FILE, 'rb') as f:
        files = {'file': (os.path.basename(TEST_FILE), f)}
        
        data = {
            'model_id': 'gemini-2.5-flash',
            'process_all_pages': 'true',
            'tier': 'Normal',
            'extraction_enabled': 'true',
            'extraction_target': 'document',
            'extraction_schema': json.dumps(EXTRACTION_SCHEMA),
            'extractor_model': 'gemini-2.5-flash'
        }
        
        print(f"\n🚀 Sending extraction request...")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/parse",
                files=files,
                data=data,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success!")
                
                # Check if extraction was successful
                if result.get('extraction'):
                    extraction = result['extraction']
                    
                    if extraction.get('success'):
                        print(f"\n📊 Extraction Results:")
                        print(f"   Structured Data: {json.dumps(extraction.get('structured_data', {}), indent=2, ensure_ascii=False)}")
                        
                        if extraction.get('field_errors'):
                            print(f"\n⚠️  Field Errors:")
                            for field, error in extraction['field_errors'].items():
                                print(f"   - {field}: {error}")
                    else:
                        print(f"\n❌ Extraction failed: {extraction.get('error')}")
                else:
                    print(f"\n⚠️  No extraction data in response")
                
                # Check if file was saved
                extracted_dir = "/Users/dark_kazansky/Coding-Space/Dr.Vision/backend/data/extracted"
                base_filename = os.path.splitext(os.path.basename(TEST_FILE))[0]
                extracted_file = os.path.join(extracted_dir, f"{base_filename}.json")
                
                if os.path.exists(extracted_file):
                    print(f"\n✅ Extraction result saved: {extracted_file}")
                    
                    # Read and display saved file
                    with open(extracted_file, 'r', encoding='utf-8') as f:
                        saved_data = json.load(f)
                    
                    print(f"\n📄 Saved File Contents:")
                    print(f"   Filename: {saved_data.get('filename')}")
                    print(f"   Model: {saved_data.get('model')}")
                    print(f"   Target: {saved_data.get('extraction_target')}")
                    print(f"   Fields: {len(saved_data.get('schema', []))}")
                    print(f"   Data: {json.dumps(saved_data.get('structured_data', {}), indent=2, ensure_ascii=False)}")
                else:
                    print(f"\n❌ Extraction result file not found: {extracted_file}")
                
            else:
                print(f"❌ Error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"❌ Error: Request timeout (120s)")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_extraction()
