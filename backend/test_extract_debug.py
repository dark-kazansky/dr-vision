#!/usr/bin/env python3
"""
Debug script to test extract endpoint with sample data
"""
import requests
import json

API_BASE_URL = "http://localhost:8082"

# Sample schema that would be generated
sample_schema = [
    {
        "name": "invoice_number",
        "type": "string",
        "description": "Invoice number",
        "required": True
    },
    {
        "name": "total_amount",
        "type": "number",
        "description": "Total amount",
        "required": True
    }
]

print("Testing extract with /parse endpoint...")
print(f"Schema: {json.dumps(sample_schema, indent=2)}")

# Test with a sample file
try:
    # You'll need to provide an actual file path
    file_path = "data/uploaded/BCTC.pdf"
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {
            'model_id': 'gemini-2.5-flash-image',
            'tier': 'Normal',
            'extraction_enabled': 'true',
            'process_all_pages': 'true',
            'parse_formatting': 'true',
            'extraction_target': 'document',
            'extraction_schema': json.dumps(sample_schema),
            'extractor_model': 'gemini-2.5-flash'
        }
        
        print(f"\nSending request to {API_BASE_URL}/parse")
        print(f"Parameters: {json.dumps({k: v for k, v in data.items() if k != 'extraction_schema'}, indent=2)}")
        
        response = requests.post(
            f"{API_BASE_URL}/parse",
            data=data,
            files=files
        )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("Success!")
            print(json.dumps(result, indent=2))
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            
except FileNotFoundError:
    print(f"File not found: {file_path}")
    print("Please update the file_path variable with an actual file")
except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()
