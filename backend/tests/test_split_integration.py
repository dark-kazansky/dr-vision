"""
Integration test for the /split endpoint.

This test verifies that the split endpoint is properly registered and accessible.
"""

import requests
import json
from pathlib import Path
from PIL import Image
import io

BASE_URL = "http://localhost:8000"


def test_split_endpoint_exists():
    """Test that the /split endpoint is registered and accessible."""
    print("\n🔍 Testing /split endpoint registration...")
    
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='white')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    # Prepare test data
    categories = [
        {"name": "Header", "description": "Document header", "order": 0},
        {"name": "Body", "description": "Main content", "order": 1}
    ]
    
    files = {'file': ('test.png', img_bytes, 'image/png')}
    data = {
        'categories': json.dumps(categories),
        'allow_uncategorized': 'true'
    }
    
    # Make request
    response = requests.post(f"{BASE_URL}/split", files=files, data=data, timeout=30)
    
    print(f"   Status code: {response.status_code}")
    
    # The endpoint should be accessible (not 404)
    assert response.status_code != 404, "Split endpoint not found (404)"
    
    # We expect either 200 (success) or 500 (POE API error without key)
    # or 401 (authentication error)
    if response.status_code in [200, 401, 500]:
        print(f"✅ Split endpoint is registered and accessible")
        result = response.json()
        print(f"   Response: {result}")
        return True
    else:
        print(f"⚠️  Unexpected status code: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def test_split_endpoint_validation():
    """Test that the /split endpoint validates input correctly."""
    print("\n🔍 Testing /split endpoint validation...")
    
    # Test with missing file
    data = {
        'categories': json.dumps([{"name": "Test", "description": "Test", "order": 0}]),
        'allow_uncategorized': 'true'
    }
    
    response = requests.post(f"{BASE_URL}/split", data=data, timeout=10)
    
    print(f"   Status code (no file): {response.status_code}")
    
    # Should return 422 (validation error) for missing file
    assert response.status_code == 422, f"Expected 422 for missing file, got {response.status_code}"
    print("✅ Endpoint correctly validates missing file")
    
    # Test with invalid categories JSON
    img = Image.new('RGB', (100, 100), color='white')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    files = {'file': ('test.png', img_bytes, 'image/png')}
    data = {
        'categories': 'invalid json',
        'allow_uncategorized': 'true'
    }
    
    response = requests.post(f"{BASE_URL}/split", files=files, data=data, timeout=10)
    
    print(f"   Status code (invalid JSON): {response.status_code}")
    
    # Should return 400 or 422 for invalid JSON
    assert response.status_code in [400, 422], f"Expected 400/422 for invalid JSON, got {response.status_code}"
    print("✅ Endpoint correctly validates invalid JSON")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("SPLIT ENDPOINT INTEGRATION TESTS")
    print("="*70)
    
    try:
        # Check if server is running
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Backend server is not healthy")
            exit(1)
        print("✅ Backend server is healthy")
    except Exception as e:
        print(f"❌ Cannot connect to backend server: {e}")
        print("   Make sure the server is running at http://localhost:8000")
        exit(1)
    
    tests = [
        ("Endpoint Registration", test_split_endpoint_exists),
        ("Input Validation", test_split_endpoint_validation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"\n❌ {test_name} FAILED: {str(e)}")
        except Exception as e:
            failed += 1
            print(f"\n❌ {test_name} ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("INTEGRATION TEST SUMMARY")
    print("="*70)
    print(f"Total tests: {len(tests)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print("="*70 + "\n")
    
    exit(0 if failed == 0 else 1)
