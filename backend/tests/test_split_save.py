#!/usr/bin/env python3
"""
Test split functionality with file saving.
"""

import requests
import os
import json
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8082"
TEST_FILE = "/Users/dark_kazansky/Coding-Space/Dr.Vision/backend/data/uploaded/BCTC.pdf"

# Split categories
SPLIT_CATEGORIES = [
    {
        "name": "Header",
        "description": "Document header with company information and title",
        "order": 0
    },
    {
        "name": "Tax Information",
        "description": "Tax identification and filing information",
        "order": 1
    },
    {
        "name": "Financial Table",
        "description": "Tables containing financial data and calculations",
        "order": 2
    },
    {
        "name": "Signature",
        "description": "Signature section with dates and names",
        "order": 3
    }
]


def test_split():
    """Test split with file saving."""
    print("=" * 80)
    print("SPLIT TEST WITH FILE SAVING")
    print("=" * 80)
    
    # Check if test file exists
    if not os.path.exists(TEST_FILE):
        print(f"❌ Test file not found: {TEST_FILE}")
        return
    
    print(f"✅ Test file: {TEST_FILE}")
    print(f"📋 Categories: {len(SPLIT_CATEGORIES)}")
    
    # Prepare form data
    with open(TEST_FILE, 'rb') as f:
        files = {'file': (os.path.basename(TEST_FILE), f)}
        
        data = {
            'parser_tier': 'Normal',
            'splitter_tier': 'Normal',
            'categories': json.dumps(SPLIT_CATEGORIES),
            'allow_uncategorized': 'true'
        }
        
        print(f"\n🚀 Sending split request...")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/split",
                files=files,
                data=data,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success!")
                
                # Check if split was successful
                if result.get('success'):
                    print(f"\n📊 Split Results:")
                    print(f"   Filename: {result.get('filename', 'N/A')}")
                    print(f"   Categorized chunks: {len(result.get('chunks', []))}")
                    print(f"   Unknown chunks: {len(result.get('unknown_chunks', []))}")
                    
                    # Display chunks by category
                    if result.get('chunks'):
                        print(f"\n📄 Chunks by Category:")
                        category_counts = {}
                        for chunk in result['chunks']:
                            category = chunk.get('category', 'Unknown')
                            category_counts[category] = category_counts.get(category, 0) + 1
                        
                        for category, count in category_counts.items():
                            print(f"   - {category}: {count} chunk(s)")
                    
                    # Display unknown chunks
                    if result.get('unknown_chunks'):
                        print(f"\n❓ Unknown Chunks: {len(result['unknown_chunks'])}")
                else:
                    print(f"\n❌ Split failed: {result.get('error')}")
                
                # Check if file was saved
                splited_dir = "/Users/dark_kazansky/Coding-Space/Dr.Vision/backend/data/splited"
                base_filename = os.path.splitext(os.path.basename(TEST_FILE))[0]
                split_file = os.path.join(splited_dir, f"{base_filename}.json")
                
                if os.path.exists(split_file):
                    print(f"\n✅ Split result saved: {split_file}")
                    
                    # Read and display saved file
                    with open(split_file, 'r', encoding='utf-8') as f:
                        saved_data = json.load(f)
                    
                    print(f"\n📄 Saved File Contents:")
                    print(f"   Filename: {saved_data.get('filename')}")
                    print(f"   Model: {saved_data.get('model')}")
                    print(f"   Categories: {len(saved_data.get('categories', []))}")
                    print(f"   Chunks: {len(saved_data.get('chunks', []))}")
                    print(f"   Unknown chunks: {len(saved_data.get('unknown_chunks', []))}")
                    
                    # Display category breakdown
                    if saved_data.get('chunks'):
                        print(f"\n📊 Category Breakdown:")
                        category_pages = {}
                        for chunk in saved_data['chunks']:
                            category = chunk.get('category', 'Unknown')
                            page = chunk.get('page_number', 0)
                            if category not in category_pages:
                                category_pages[category] = []
                            category_pages[category].append(page)
                        
                        for category, pages in category_pages.items():
                            print(f"   - {category}: Pages {', '.join(map(str, sorted(pages)))}")
                else:
                    print(f"\n❌ Split result file not found: {split_file}")
                
            else:
                print(f"❌ Error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"❌ Error: Request timeout (120s)")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_split()
