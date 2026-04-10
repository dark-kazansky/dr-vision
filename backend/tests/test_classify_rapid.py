#!/usr/bin/env python3
"""
Test script for classifying all files in test_files directory using Rapid mode.
"""

import requests
import os
import json
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8082"
TEST_FILES_DIR = "/Users/dark_kazansky/Coding-Space/Dr.Vision/test_files"

# Classification rules
CLASSIFICATION_RULES = [
    {"type": "Invoice", "description": "Financial invoice or bill document"},
    {"type": "Receipt", "description": "Purchase receipt or payment proof"},
    {"type": "Contract", "description": "Legal contract or agreement"},
    {"type": "Report", "description": "Business or financial report"},
    {"type": "Form", "description": "Application or registration form"},
    {"type": "Letter", "description": "Business or personal letter"},
    {"type": "Certificate", "description": "Certificate or diploma"},
    {"type": "ID Document", "description": "Identity card or passport"},
    {"type": "Other", "description": "Other document types"}
]

def classify_file(file_path: str, tier: str = "Rapid") -> dict:
    """
    Classify a single file using the /classify endpoint.
    
    Args:
        file_path: Path to the file to classify
        tier: Processing tier (Rapid, Normal, Advance, Multimodal)
        
    Returns:
        Classification result dictionary
    """
    print(f"\n{'='*80}")
    print(f"Classifying: {os.path.basename(file_path)}")
    print(f"Tier: {tier}")
    print(f"{'='*80}")
    
    # Prepare form data
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f)}
        
        data = {
            'parser_model_id': 'deepseek-ocr',  # Rapid tier parser
            'classifier_model_id': 'gemini-2.5-flash-lite',  # Rapid tier classifier
            'classification_rules': json.dumps(CLASSIFICATION_RULES),
            'tier': tier,
            'max_pages': '5',
            'is_multimodal': 'false'
        }
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/classify",
                files=files,
                data=data,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success!")
                
                if result.get('success') and result.get('results'):
                    for res in result['results']:
                        print(f"\n📄 File: {res.get('fileName', 'N/A')}")
                        print(f"📋 Document Type: {res.get('documentType', 'N/A')}")
                        print(f"🎯 Confidence: {res.get('confidence', 0):.2%}")
                        if res.get('reasoning'):
                            print(f"💭 Reasoning: {res.get('reasoning')}")
                else:
                    print(f"⚠️  No results in response")
                    print(f"Response: {json.dumps(result, indent=2)}")
                
                return result
            else:
                print(f"❌ Error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.Timeout:
            print(f"❌ Error: Request timeout (120s)")
            return {'success': False, 'error': 'Request timeout'}
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {'success': False, 'error': str(e)}


def main():
    """Main test function."""
    print("\n" + "="*80)
    print("CLASSIFY TEST - RAPID MODE")
    print("="*80)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Test Files Directory: {TEST_FILES_DIR}")
    print(f"Classification Rules: {len(CLASSIFICATION_RULES)} types")
    
    # Check if test files directory exists
    if not os.path.exists(TEST_FILES_DIR):
        print(f"\n❌ Error: Test files directory not found: {TEST_FILES_DIR}")
        return
    
    # Get all files in test directory
    test_files = []
    for file_path in Path(TEST_FILES_DIR).iterdir():
        if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.png', '.jpg', '.jpeg']:
            test_files.append(str(file_path))
    
    if not test_files:
        print(f"\n❌ Error: No test files found in {TEST_FILES_DIR}")
        return
    
    print(f"\nFound {len(test_files)} test files:")
    for f in test_files:
        print(f"  - {os.path.basename(f)}")
    
    # Test each file
    results = []
    for file_path in test_files:
        result = classify_file(file_path, tier="Rapid")
        results.append({
            'file': os.path.basename(file_path),
            'result': result
        })
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    successful = sum(1 for r in results if r['result'].get('success'))
    failed = len(results) - successful
    
    print(f"\nTotal Files: {len(results)}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    
    if successful > 0:
        print("\n📊 Classification Results:")
        for r in results:
            if r['result'].get('success') and r['result'].get('results'):
                res = r['result']['results'][0]
                print(f"  {r['file']:<30} → {res.get('documentType', 'N/A'):<20} ({res.get('confidence', 0):.1%})")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
