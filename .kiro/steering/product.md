# Product Overview

Dr.Vision is an OCR (Optical Character Recognition) web application that processes images and PDF documents to extract text and structured data.

## Core Capabilities

- **Multi-Model OCR**: Supports multiple OCR models (LightOnOCR-2-1B, DeepSeek-OCR, Nanonets-OCR2-3B) via LM Studio
- **Multi-Model Extractor**: Supports multiple LLM model (Agent, Qwen3-Max-Thinking, Gemini-3-Pro) via POE
- **Document Processing**: Handles PNG, JPG, JPEG, and PDF files with single or multi-page processing
- **Structured Data Extraction**: Extracts structured data from documents using configurable schemas with field definitions
- **Processing Tiers**: Three quality levels (Rapid, Normal, Advance) for balancing speed vs accuracy
- **Extraction Targets**: Supports document-level, page-level, and table-row extraction scopes

## Architecture

Full-stack application with:
- **Backend**: FastAPI REST API for OCR processing and configuration management
- **Frontend**: Nuxt 3 SPA with drag-and-drop file upload and real-time status updates
- **OCR Engine**: LM Studio running vision-enabled language models locally and POE API

## Key Features

- Drag-and-drop file upload with validation
- Real-time processing status
- Multi-file queue management
- PDF preview with page navigation and zoom
- Three-tab results view (Build, Raw Text, Parsed)
- Copy-to-clipboard functionality
- Schema builder for custom extraction configurations
