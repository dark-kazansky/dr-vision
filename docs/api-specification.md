# Doc Intelligence — API Specification

**Version:** 2.0.0  
**Base URL:** `http://{host}:8000`  
**Interactive Docs:** `/docs` (Swagger UI) | `/redoc` (ReDoc)

---

## Overview

Doc Intelligence là nền tảng AI xử lý chứng từ ngân hàng, cung cấp các dịch vụ:
- **OCR/Parse** — Bóc tách văn bản từ ảnh và PDF
- **Extract** — Trích xuất dữ liệu có cấu trúc theo schema
- **Split** — Phân loại và tách tài liệu đa loại
- **Classify** — Phân loại loại chứng từ
- **Workflow** — Pipeline xử lý đa bước (OCR → Classify → Extract → Validate)

---

## Authentication

Hiện tại API phục vụ internal (BPM → AI Server). Authentication qua:
- Network-level: API Gateway / VPN / Service Mesh
- Future: JWT Bearer token (khi expose ra external)

---

## Rate Limiting

| Parameter | Default |
|-----------|---------|
| Requests/minute | 30 |
| Burst size | 10 |
| Algorithm | Token Bucket per IP |
| Response khi vượt | HTTP 429 + `Retry-After` header |

---

## Error Response Format

Mọi lỗi trả về JSON nhất quán:

```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_type": "validation_error | http_error | internal_error"
}
```

| HTTP Code | Meaning |
|-----------|---------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 413 | Payload Too Large (file size exceeded) |
| 422 | Validation Error (missing required fields) |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |

---

## Core Endpoints

### 1. Parse (OCR)

Bóc tách văn bản từ document. Hỗ trợ sync (nhỏ) và async/background (PDF lớn).

```
POST /parse
POST /ocr       ← alias
Content-Type: multipart/form-data
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | ✅ | PDF, PNG, JPG, JPEG, DOCX |
| `model_id` | string | ✅ | AI model ID (e.g. `gemini-2.5-flash`) |
| `force_ocr` | bool | | Force OCR cho text-based PDF (default: false) |
| `parse_formatting` | bool | | Áp dụng text formatting (default: true) |
| `tier` | string | | `Rapid` \| `Normal` \| `Advance` |
| `provider` | string | | Override provider (google, bedrock, lmstudio) |
| `extraction_enabled` | bool | | Inline extraction (default: false) |
| `extraction_schema` | JSON string | | Schema fields nếu extraction_enabled |
| `extractor_model` | string | | Model cho extraction step |

**Response (sync):**
```json
{
  "success": true,
  "text": "Extracted text content...",
  "parsed_text": "Formatted text...",
  "file_type": "pdf",
  "is_scanned": false,
  "pages": 3,
  "filename": "contract.pdf",
  "model": "gemini-2.5-flash"
}
```

**Response (background — large PDF):**
```json
{
  "success": true,
  "background": true,
  "job_id": "uuid-here",
  "message": "Document has 15 pages. Processing in background."
}
```

---

### 2. Extract

Trích xuất dữ liệu có cấu trúc từ document hoặc text.

#### 2a. Extract from File (OCR + Extract)

```
POST /extract
Content-Type: multipart/form-data
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | ✅ | Document to process |
| `parser_model_id` | string | ✅ | Model cho OCR step |
| `extractor_model_id` | string | | Model cho extraction (default: qwen3-max) |
| `extraction_schema` | JSON string | ✅ | Array of field definitions |
| `extraction_target` | string | | `document` \| `page` \| `table_row` |
| `generate_schema` | bool | | Dùng AI sinh schema (default: false) |
| `schema_prompt` | string | | Mô tả bằng ngôn ngữ tự nhiên |

**Schema Format:**
```json
[
  {"name": "invoice_number", "type": "string", "description": "Số hóa đơn", "required": true},
  {"name": "total_amount", "type": "number", "description": "Tổng tiền (VND)", "required": true},
  {"name": "date", "type": "date", "description": "Ngày hóa đơn", "required": false}
]
```

**Response:**
```json
{
  "success": true,
  "structured_data": {
    "invoice_number": "INV-2026-042",
    "total_amount": 150000000,
    "date": "2026-06-01"
  },
  "field_errors": {},
  "filename": "invoice.pdf"
}
```

#### 2b. Extract from Text (no OCR)

```
POST /extract-text
Content-Type: multipart/form-data
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | ✅ | Pre-extracted text |
| `extraction_schema` | JSON string | ✅ | Field definitions |
| `extraction_target` | string | | Target scope |
| `extractor_model_id` | string | | Model (default: gemini-2.5-flash) |

#### 2c. Generate Schema

```
POST /generate-schema
Content-Type: multipart/form-data
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | ✅ | Mô tả tự nhiên về fields cần extract |
| `file` | File | | Sample document cho context |
| `tier` | string | | Processing tier |

**Response:**
```json
{
  "success": true,
  "schema": [
    {"name": "transaction_date", "type": "date", "description": "Ngày giao dịch", "required": true},
    {"name": "amount", "type": "number", "description": "Số tiền", "required": true}
  ]
}
```

---

### 3. Split

Tách document đa loại thành các phần theo category.

```
POST /split
Content-Type: multipart/form-data
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | ✅ | Multi-document PDF |
| `categories` | JSON string | ✅ | Array of category definitions |
| `split_mode` | string | | `sections` (default) \| `document_type` |
| `allow_uncategorized` | bool | | Cho phép chunks không khớp (default: true) |
| `splitter_tier` | string | | Processing tier |

**Categories Format:**
```json
[
  {"name": "Hợp đồng", "description": "Hợp đồng tín dụng, thế chấp", "order": 0},
  {"name": "CMND/CCCD", "description": "Giấy tờ tùy thân", "order": 1},
  {"name": "Sao kê", "description": "Bảng kê giao dịch ngân hàng", "order": 2}
]
```

**Response (sections mode):**
```json
{
  "success": true,
  "chunks": [
    {"content": "HỢP ĐỒNG TÍN DỤNG SỐ...", "category": "Hợp đồng", "page_number": 1, "confidence": 0.95}
  ],
  "unknown_chunks": [],
  "document_types": null,
  "filename": "loan-package.pdf"
}
```

**Response (document_type mode):**
```json
{
  "success": true,
  "chunks": [],
  "unknown_chunks": [],
  "document_types": [
    {"type_name": "Hợp đồng", "page_numbers": [1, 2, 3], "confidence": 0.92},
    {"type_name": "CMND/CCCD", "page_numbers": [4], "confidence": 0.98}
  ]
}
```

---

## System Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check + available models |
| `/models/check` | GET | Model connectivity status |
| `/tier-config` | GET | Current tier → model mapping |
| `/providers` | GET | List configured AI providers |
| `/providers/{id}/test` | POST | Test provider connectivity |

---

## Job Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/jobs` | GET | List all jobs (pagination) |
| `/api/v1/jobs/{id}` | GET | Get job detail + result |
| `/api/v1/jobs/{id}` | DELETE | Cancel/delete job |
| `/api/v1/jobs/{id}/state` | GET | Execution state (per-node) |
| `/api/v1/jobs/{id}/state/nodes` | GET | All node outputs |

---

## Observability

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/observability/timeline/{job_id}` | GET | Per-node execution timeline |
| `/api/v1/observability/metrics` | GET | Performance metrics (avg/min/max) |
| `/api/v1/observability/errors` | GET | Error analytics + failure rates |
| `/api/v1/observability/audit` | GET | Audit log (who, when, result) |
| `/api/v1/observability/dashboard` | GET | System health summary |

---

## AI Providers

| Provider | Models | Use Case |
|----------|--------|----------|
| **Google Gemini** | gemini-2.5-flash, gemini-2.5-pro | OCR, Extraction, Classification |
| **AWS Bedrock** | Claude Haiku, Claude Sonnet | Classification, Validation |
| **LM Studio** (local) | LightOnOCR-2-1B, DeepSeek | Development, offline OCR |
| **Ollama** (local) | Qwen3, LLaMA | Local extraction |
| **vLLM** | LightOnOCR-2-1B | Production OCR (GPU cluster) |

---

## Processing Tiers

| Tier | Speed | Quality | Typical Model |
|------|-------|---------|---------------|
| **Rapid** | < 3s | Good | gemini-2.5-flash |
| **Normal** | 5-15s | High | gemini-2.5-flash / qwen3-max |
| **Advance** | 15-60s | Best | gemini-2.5-pro / Claude Sonnet |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       API Layer (FastAPI)                     │
│   /parse  /extract  /split  /classify  /workflows  /jobs    │
├─────────────────────────────────────────────────────────────┤
│                     Service Layer                             │
│   parse_service  extract_service  split_service  workflow    │
├─────────────────────────────────────────────────────────────┤
│                    Component Layer                            │
│   Parser  Extractor  Splitter  Classifier  SchemaGenerator  │
├─────────────────────────────────────────────────────────────┤
│                     Agent Layer (Factory)                     │
│   Google  Bedrock  LMStudio  Ollama  POE  vLLM             │
├─────────────────────────────────────────────────────────────┤
│                    Infrastructure                             │
│   PostgreSQL 16  │  MinIO  │  Redis (future)  │  K8s        │
└─────────────────────────────────────────────────────────────┘
```

---

## Deployment

```bash
# Development (Docker Compose)
docker compose up -d

# Production (Kubernetes)
kubectl apply -f k8s/
```

| Service | Port | Protocol |
|---------|------|----------|
| Backend API | 8000 | HTTP |
| Frontend | 3000 | HTTP |
| PostgreSQL | 5433 | TCP |
| MinIO | 9000/9001 | HTTP |

---

## Postman Collection

Import `.postman/doc-intelligence-collection.json` vào Postman để test interactive.  
Environment: `.postman/doc-intelligence-environment.json`

**Run automated tests:**
```bash
npx newman run .postman/doc-intelligence-collection.json \
  -e .postman/doc-intelligence-environment.json \
  --reporters cli,json
```
