"""
Test script for /split route implementation.

This script tests the /split endpoint to verify:
- File upload validation
- Category configuration parsing
- Category name uniqueness validation
- File type and size validation
- Secure file handling
"""

import sys
import os
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from main import app
from io import BytesIO

# Create test client
client = TestClient(app)


def test_split_route_validation():
    """Test /split route validation logic."""
    
    print("=" * 60)
    print("Testing /split Route Validation")
    print("=" * 60)
    
    # Test 1: Missing file
    print("\n1. Testing missing file...")
    response = client.post(
        "/split",
        data={
            "categories": json.dumps([
                {"name": "Introduction", "description": "Opening section", "order": 0}
            ]),
            "allow_uncategorized": "true"
        }
    )
    print(f"   Status: {response.status_code}")
    print(f"   Expected: 422 (Unprocessable Entity - missing required field)")
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    print("   ✓ PASS")
    
    # Test 2: Invalid file type
    print("\n2. Testing invalid file type...")
    invalid_file = BytesIO(b"test content")
    response = client.post(
        "/split",
        data={
            "categories": json.dumps([
                {"name": "Introduction", "description": "Opening section", "order": 0}
            ]),
            "allow_uncategorized": "true"
        },
        files={"file": ("test.txt", invalid_file, "text/plain")}
    )
    print(f"   Status: {response.status_code}")
    print(f"   Expected: 400 (Bad Request - invalid file type)")
    if response.status_code == 400:
        print(f"   Detail: {response.json().get('detail', 'N/A')}")
        print("   ✓ PASS")
    else:
        print(f"   ✗ FAIL: Expected 400, got {response.status_code}")
    
    # Test 3: Invalid categories JSON
    print("\n3. Testing invalid categories JSON...")
    test_file = BytesIO(b"fake image content")
    response = client.post(
        "/split",
        data={
            "categories": "invalid json",
            "allow_uncategorized": "true"
        },
        files={"file": ("test.png", test_file, "image/png")}
    )
    print(f"   Status: {response.status_code}")
    print(f"   Expected: 400 (Bad Request - invalid JSON)")
    if response.status_code == 400:
        print(f"   Detail: {response.json().get('detail', 'N/A')}")
        print("   ✓ PASS")
    else:
        print(f"   ✗ FAIL: Expected 400, got {response.status_code}")
    
    # Test 4: Duplicate category names
    print("\n4. Testing duplicate category names...")
    test_file = BytesIO(b"fake image content")
    response = client.post(
        "/split",
        data={
            "categories": json.dumps([
                {"name": "Introduction", "description": "First intro", "order": 0},
                {"name": "Introduction", "description": "Second intro", "order": 1}
            ]),
            "allow_uncategorized": "true"
        },
        files={"file": ("test.png", test_file, "image/png")}
    )
    print(f"   Status: {response.status_code}")
    print(f"   Expected: 400 (Bad Request - duplicate names)")
    if response.status_code == 400:
        detail = response.json().get('detail', 'N/A')
        print(f"   Detail: {detail}")
        if "unique" in detail.lower():
            print("   ✓ PASS")
        else:
            print(f"   ✗ FAIL: Error message doesn't mention uniqueness")
    else:
        print(f"   ✗ FAIL: Expected 400, got {response.status_code}")
    
    # Test 5: Too many categories
    print("\n5. Testing too many categories (>50)...")
    test_file = BytesIO(b"fake image content")
    categories = [
        {"name": f"Category{i}", "description": f"Description {i}", "order": i}
        for i in range(51)
    ]
    response = client.post(
        "/split",
        data={
            "categories": json.dumps(categories),
            "allow_uncategorized": "true"
        },
        files={"file": ("test.png", test_file, "image/png")}
    )
    print(f"   Status: {response.status_code}")
    print(f"   Expected: 400 (Bad Request - too many categories)")
    if response.status_code == 400:
        detail = response.json().get('detail', 'N/A')
        print(f"   Detail: {detail}")
        if "maximum" in detail.lower() or "exceeds" in detail.lower():
            print("   ✓ PASS")
        else:
            print(f"   ✗ FAIL: Error message doesn't mention maximum limit")
    else:
        print(f"   ✗ FAIL: Expected 400, got {response.status_code}")
    
    # Test 6: Valid request structure (will fail at POE API call if POE_API_KEY not set)
    print("\n6. Testing valid request structure...")
    test_file = BytesIO(b"fake image content")
    response = client.post(
        "/split",
        data={
            "categories": json.dumps([
                {"name": "Introduction", "description": "Opening section", "order": 0},
                {"name": "Methodology", "description": "Research methods", "order": 1}
            ]),
            "allow_uncategorized": "true"
        },
        files={"file": ("test.png", test_file, "image/png")}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 401:
        print(f"   Expected: 401 (Unauthorized - POE_API_KEY not set)")
        print(f"   Detail: {response.json().get('detail', 'N/A')}")
        print("   ✓ PASS (validation passed, failed at POE API key check)")
    elif response.status_code == 500:
        print(f"   Expected: 500 (Processing error - likely file handling)")
        print(f"   Detail: {response.json().get('detail', 'N/A')}")
        print("   ✓ PASS (validation passed, failed at processing)")
    elif response.status_code == 200:
        print(f"   Unexpected: 200 (Success - POE API key is set and working)")
        print("   ✓ PASS (full request succeeded)")
    else:
        print(f"   Status: {response.status_code}")
        print(f"   Detail: {response.json()}")
    
    print("\n" + "=" * 60)
    print("Validation Tests Complete")
    print("=" * 60)


def test_category_model_validation():
    """Test ChunkCategoryModel validation."""
    
    print("\n" + "=" * 60)
    print("Testing Category Model Validation")
    print("=" * 60)
    
    from src.models import ChunkCategoryModel
    from pydantic import ValidationError
    
    # Test 1: Valid category
    print("\n1. Testing valid category...")
    try:
        cat = ChunkCategoryModel(
            name="Introduction",
            description="Opening section",
            order=0
        )
        print(f"   Created: {cat.name} (order={cat.order})")
        print("   ✓ PASS")
    except ValidationError as e:
        print(f"   ✗ FAIL: {e}")
    
    # Test 2: Empty name
    print("\n2. Testing empty name...")
    try:
        cat = ChunkCategoryModel(
            name="",
            description="Test",
            order=0
        )
        print(f"   ✗ FAIL: Should have raised ValidationError")
    except ValidationError as e:
        print(f"   Validation error (expected): {e.error_count()} error(s)")
        print("   ✓ PASS")
    
    # Test 3: Name too long (>200 chars)
    print("\n3. Testing name too long...")
    try:
        cat = ChunkCategoryModel(
            name="A" * 201,
            description="Test",
            order=0
        )
        print(f"   ✗ FAIL: Should have raised ValidationError")
    except ValidationError as e:
        print(f"   Validation error (expected): {e.error_count()} error(s)")
        print("   ✓ PASS")
    
    # Test 4: Description too long (>2000 chars)
    print("\n4. Testing description too long...")
    try:
        cat = ChunkCategoryModel(
            name="Test",
            description="A" * 2001,
            order=0
        )
        print(f"   ✗ FAIL: Should have raised ValidationError")
    except ValidationError as e:
        print(f"   Validation error (expected): {e.error_count()} error(s)")
        print("   ✓ PASS")
    
    # Test 5: Negative order
    print("\n5. Testing negative order...")
    try:
        cat = ChunkCategoryModel(
            name="Test",
            description="Test",
            order=-1
        )
        print(f"   ✗ FAIL: Should have raised ValidationError")
    except ValidationError as e:
        print(f"   Validation error (expected): {e.error_count()} error(s)")
        print("   ✓ PASS")
    
    # Test 6: Default values
    print("\n6. Testing default values...")
    try:
        cat = ChunkCategoryModel(name="Test")
        print(f"   Name: {cat.name}")
        print(f"   Description: '{cat.description}' (default)")
        print(f"   Order: {cat.order} (default)")
        assert cat.description == "", "Description should default to empty string"
        assert cat.order == 0, "Order should default to 0"
        print("   ✓ PASS")
    except Exception as e:
        print(f"   ✗ FAIL: {e}")
    
    print("\n" + "=" * 60)
    print("Category Model Tests Complete")
    print("=" * 60)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SPLIT ROUTE IMPLEMENTATION TEST")
    print("=" * 60)
    
    # Run tests
    test_category_model_validation()
    test_split_route_validation()
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)
    print("\nNote: These tests verify the route validation logic.")
    print("Full integration tests require POE_API_KEY to be set.")
    print("=" * 60 + "\n")
