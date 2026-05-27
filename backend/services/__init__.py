"""
Business logic and infrastructure services for Dr.Vision.

Business logic services (one per domain):
- parse_service: OCR and document text extraction
- classify_service: Document classification
- extract_service: Structured data extraction + schema generation
- split_service: Document splitting (sections / document-type)
- system_service: Health checks, model inspection, tier config
- workflow_service: Multi-step pipeline + condition evaluation
- saved_files_service: File listing and retrieval

Infrastructure services:
- job_manager: In-memory background job tracking
"""
