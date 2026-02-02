"""
Task 8.1: Smoke Test for Extraction Workflow

Quick smoke test to verify basic extraction functionality without full OCR processing.
"""

import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

BASE_URL = "http://localhost:8000"
BACKEND_DIR = Path(__file__).parent


def test_health():
    """Test backend health."""
    print("\n🔍 Testing backend health...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✅ Backend is healthy")


def test_schema_generation():
    """Test schema generation endpoint."""
    print("\n🔍 Testing schema generation...")
    
    prompt = "Extract invoice information including invoice number, date, customer name, and total amount"
    data = {'prompt': prompt}
    
    print(f"   Prompt: {prompt}")
    response = requests.post(f"{BASE_URL}/generate-schema", data=data)
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"   Success: {result.get('success')}")
        
        if result.get('success'):
            schema = result.get('schema', [])
            print(f"   Generated {len(schema)} fields:")
            for field in schema:
                print(f"      - {field['name']} ({field['type']})")
            print("✅ Schema generation works")
        else:
            print(f"   ⚠️  Schema generation failed: {result.get('error')}")
    else:
        print(f"   ❌ Request failed: {response.text}")


def test_extraction_config_validation():
    """Test extraction config validation."""
    print("\n🔍 Testing extraction config validation...")
    
    # Valid schema
    valid_schema = [
        {"name": "field1", "type": "string", "description": "Test field", "required": True}
    ]
    
    # Invalid schema (empty name)
    invalid_schema = [
        {"name": "", "type": "string", "description": "Invalid", "required": False}
    ]
    
    test_file = BACKEND_DIR / "test_invoice.png"
    
    # Test with invalid schema
    with open(test_file, 'rb') as f:
        files = {'file': ('test_invoice.png', f, 'image/png')}
        data = {
            'model_id': 'lightonocr-2-1b',
            'tier': 'Normal',
            'process_all_pages': 'false',
            'extraction_enabled': 'true',
            'extraction_target': 'document',
            'extraction_schema': json.dumps(invalid_schema)
        }
        
        response = requests.post(f"{BASE_URL}/ocr", files=files, data=data)
    
    print(f"   Invalid schema status: {response.status_code}")
    if response.status_code in [400, 422]:
        print("✅ Validation correctly rejects invalid schema")
    else:
        print(f"   ⚠️  Expected 400/422, got {response.status_code}")


def test_extraction_targets():
    """Test that different extraction targets are accepted."""
    print("\n🔍 Testing extraction target options...")
    
    schema = [
        {"name": "test_field", "type": "string", "description": "Test", "required": False}
    ]
    
    test_file = BACKEND_DIR / "test_invoice.png"
    
    targets = ['document', 'page', 'table_row']
    
    for target in targets:
        print(f"\n   Testing target: {target}")
        
        with open(test_file, 'rb') as f:
            files = {'file': ('test_invoice.png', f, 'image/png')}
            data = {
                'model_id': 'lightonocr-2-1b',
                'tier': 'Rapid',  # Use Rapid for faster testing
                'process_all_pages': 'false',
                'extraction_enabled': 'true',
                'extraction_target': target,
                'extraction_schema': json.dumps(schema)
            }
            
            response = requests.post(f"{BASE_URL}/ocr", files=files, data=data, timeout=60)
        
        print(f"      Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"      Success: {result.get('success')}")
            
            if result.get('structured_data'):
                data_type = type(result['structured_data']).__name__
                print(f"      Data type: {data_type}")
                
                if target == 'document':
                    if isinstance(result['structured_data'], dict):
                        print(f"      ✅ Document target returns dict")
                    else:
                        print(f"      ⚠️  Document target should return dict, got {data_type}")
                else:
                    if isinstance(result['structured_data'], list):
                        print(f"      ✅ {target} target returns list")
                    else:
                        print(f"      ⚠️  {target} target should return list, got {data_type}")
        else:
            print(f"      ❌ Request failed: {response.text[:200]}")


def run_smoke_tests():
    """Run all smoke tests."""
    print("\n" + "="*70)
    print("TASK 8.1: EXTRACTION WORKFLOW SMOKE TESTS")
    print("="*70)
    
    tests = [
        ("Health Check", test_health),
        ("Schema Generation", test_schema_generation),
        ("Config Validation", test_extraction_config_validation),
        ("Extraction Targets", test_extraction_targets),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n❌ {test_name} FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("SMOKE TEST SUMMARY")
    print("="*70)
    print(f"Total tests: {len(tests)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print("="*70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_smoke_tests()
    exit(0 if success else 1)
