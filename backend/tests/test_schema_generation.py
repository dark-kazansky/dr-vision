"""
Manual test script for schema generation endpoint

This script tests the /generate-schema endpoint to verify:
- Prompt-only generation works
- Prompt + file generation works
- Error handling for invalid inputs
- Response format is correct
"""

import os
import sys
import requests
from pathlib import Path

# API base URL
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')


def test_generate_schema_prompt_only():
    """Test schema generation with prompt only"""
    print("\n" + "=" * 70)
    print("Test 1: Generate schema with prompt only")
    print("=" * 70)
    
    prompt = "Extract invoice information including invoice number, date, customer name, and total amount"
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/generate-schema",
            data={'prompt': prompt}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Request successful")
            print(f"  Success: {data.get('success')}")
            print(f"  Schema fields: {len(data.get('schema', []))}")
            
            if data.get('schema'):
                print("\n  Generated fields:")
                for field in data['schema']:
                    req = "required" if field.get('required') else "optional"
                    print(f"    - {field.get('name')} ({field.get('type')}, {req}): {field.get('description')}")
                return True
            else:
                print("✗ No schema fields returned")
                return False
        else:
            print(f"✗ Request failed: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Connection error - is the backend server running?")
        print(f"  Tried to connect to: {API_BASE_URL}")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_generate_schema_with_file():
    """Test schema generation with prompt and file"""
    print("\n" + "=" * 70)
    print("Test 2: Generate schema with prompt and sample file")
    print("=" * 70)
    
    # Check if we have a sample file
    sample_files = [
        'uploads/sample_invoice.png',
        'uploads/sample_invoice.jpg',
        'uploads/test.png',
        'uploads/test.jpg'
    ]
    
    sample_file = None
    for file_path in sample_files:
        if os.path.exists(file_path):
            sample_file = file_path
            break
    
    if not sample_file:
        print("⚠ No sample file found in uploads/ directory")
        print("  Skipping file upload test")
        print(f"  Looked for: {', '.join(sample_files)}")
        return None  # Skip test
    
    print(f"Using sample file: {sample_file}")
    
    prompt = "Extract all relevant information from this document"
    
    try:
        with open(sample_file, 'rb') as f:
            files = {'file': (os.path.basename(sample_file), f)}
            data = {'prompt': prompt}
            
            response = requests.post(
                f"{API_BASE_URL}/generate-schema",
                data=data,
                files=files
            )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Request successful")
            print(f"  Success: {data.get('success')}")
            print(f"  Schema fields: {len(data.get('schema', []))}")
            
            if data.get('schema'):
                print("\n  Generated fields:")
                for field in data['schema']:
                    req = "required" if field.get('required') else "optional"
                    print(f"    - {field.get('name')} ({field.get('type')}, {req}): {field.get('description')}")
                return True
            else:
                print("✗ No schema fields returned")
                return False
        else:
            print(f"✗ Request failed: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Connection error - is the backend server running?")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_generate_schema_empty_prompt():
    """Test schema generation with empty prompt (should fail)"""
    print("\n" + "=" * 70)
    print("Test 3: Generate schema with empty prompt (should fail)")
    print("=" * 70)
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/generate-schema",
            data={'prompt': ''}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 400:
            print(f"✓ Correctly rejected empty prompt")
            print(f"  Error: {response.json().get('detail')}")
            return True
        else:
            print(f"✗ Should have returned 400 status code")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Connection error - is the backend server running?")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_generate_schema_whitespace_prompt():
    """Test schema generation with whitespace-only prompt (should fail)"""
    print("\n" + "=" * 70)
    print("Test 4: Generate schema with whitespace-only prompt (should fail)")
    print("=" * 70)
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/generate-schema",
            data={'prompt': '   '}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 400:
            print(f"✓ Correctly rejected whitespace-only prompt")
            print(f"  Error: {response.json().get('detail')}")
            return True
        else:
            print(f"✗ Should have returned 400 status code")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Connection error - is the backend server running?")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_generate_schema_complex_prompt():
    """Test schema generation with complex, detailed prompt"""
    print("\n" + "=" * 70)
    print("Test 5: Generate schema with complex prompt")
    print("=" * 70)
    
    prompt = """
    Extract detailed customer order information including:
    - Customer details (name, email, phone number)
    - Order information (order ID, order date, delivery date)
    - Product details (product name, quantity, unit price, total price)
    - Payment information (payment method, payment status, transaction ID)
    - Shipping information (shipping address, shipping method, tracking number)
    """
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/generate-schema",
            data={'prompt': prompt}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Request successful")
            print(f"  Success: {data.get('success')}")
            print(f"  Schema fields: {len(data.get('schema', []))}")
            
            if data.get('schema') and len(data['schema']) >= 5:
                print("\n  Generated fields:")
                for field in data['schema']:
                    req = "required" if field.get('required') else "optional"
                    print(f"    - {field.get('name')} ({field.get('type')}, {req}): {field.get('description')}")
                print(f"\n✓ Generated {len(data['schema'])} fields for complex prompt")
                return True
            else:
                print("✗ Expected more fields for complex prompt")
                return False
        else:
            print(f"✗ Request failed: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Connection error - is the backend server running?")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_response_format():
    """Test that response format matches expected structure"""
    print("\n" + "=" * 70)
    print("Test 6: Verify response format")
    print("=" * 70)
    
    prompt = "Extract name and age"
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/generate-schema",
            data={'prompt': prompt}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check top-level structure
            if 'success' not in data:
                print("✗ Missing 'success' field in response")
                return False
            
            if 'schema' not in data:
                print("✗ Missing 'schema' field in response")
                return False
            
            if not isinstance(data['schema'], list):
                print("✗ 'schema' field is not a list")
                return False
            
            # Check field structure
            for i, field in enumerate(data['schema']):
                required_keys = ['name', 'type', 'description', 'required']
                for key in required_keys:
                    if key not in field:
                        print(f"✗ Field {i} missing '{key}' property")
                        return False
                
                # Check type is valid
                valid_types = ['string', 'number', 'boolean', 'date', 'object']
                if field['type'] not in valid_types:
                    print(f"✗ Field {i} has invalid type: {field['type']}")
                    return False
                
                # Check required is boolean
                if not isinstance(field['required'], bool):
                    print(f"✗ Field {i} 'required' is not boolean")
                    return False
            
            print("✓ Response format is correct")
            print(f"  - Has 'success' field: {data['success']}")
            print(f"  - Has 'schema' field: list with {len(data['schema'])} items")
            print(f"  - All fields have required properties")
            print(f"  - All field types are valid")
            return True
        else:
            print(f"✗ Request failed: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Connection error - is the backend server running?")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("=" * 70)
    print("Schema Generation Endpoint Tests")
    print("=" * 70)
    print(f"API Base URL: {API_BASE_URL}")
    print("\nNote: These tests require:")
    print("  1. Backend server running (python main.py)")
    print("  2. POE_API_KEY environment variable set")
    print("  3. Internet connection for Poe API")
    
    tests = [
        ("Prompt only", test_generate_schema_prompt_only),
        ("Prompt with file", test_generate_schema_with_file),
        ("Empty prompt", test_generate_schema_empty_prompt),
        ("Whitespace prompt", test_generate_schema_whitespace_prompt),
        ("Complex prompt", test_generate_schema_complex_prompt),
        ("Response format", test_response_format),
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
    
    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    total = len(results)
    
    for name, result in results:
        if result is True:
            print(f"✓ {name}")
        elif result is False:
            print(f"✗ {name}")
        else:
            print(f"⚠ {name} (skipped)")
    
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped out of {total} tests")
    print("=" * 70)
    
    if failed == 0 and passed > 0:
        print("\n✓ All tests passed!")
        print("\nThe /generate-schema endpoint is working correctly.")
        return 0
    elif failed > 0:
        print("\n✗ Some tests failed")
        print("\nPlease check:")
        print("  1. Backend server is running")
        print("  2. POE_API_KEY is set correctly")
        print("  3. Internet connection is available")
        return 1
    else:
        print("\n⚠ All tests were skipped")
        return 2


if __name__ == "__main__":
    sys.exit(main())
