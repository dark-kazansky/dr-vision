# Changelog

All notable changes to the Doc Intelligence project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-06-08

### Added
- **Multi-provider AI architecture** — Factory pattern supporting 7 AI providers (Google Gemini, AWS Bedrock, LM Studio, Ollama, POE, vLLM)
- **Document Split endpoint** (`POST /split`) — Sections mode and document-type mode for multi-document PDFs
- **Structured Extraction** (`POST /extract`, `POST /extract-text`) — Schema-based field extraction with AI
- **AI Schema Generator** (`POST /generate-schema`) — Natural language → extraction schema
- **Workflow Engine** — JSON-template driven pipelines with execution state per node
- **Banking Data Mining** — PostgreSQL-backed statement analysis and transaction categorization
- **Job Queue System** — Async processing with background dispatch for large PDFs
- **Observability Dashboard** — Execution timeline, performance metrics, error analytics, audit log
- **Rate Limiting** — Token-bucket algorithm per client IP (configurable)
- **Request Tracing** — UUID-based X-Request-ID header on every response
- **Postman Test Suite** — 56 requests across 13 endpoint groups with automated assertions
- **Unit Test Suite** — 37 endpoint tests (Parse/Extract/Split) + 20+ infrastructure tests
- **Kubernetes manifests** — Production-ready deployment configs
- **Tier Configuration** — Rapid/Normal/Advance processing tiers with model routing

### Changed
- Migrated from monolithic routes to **versioned API** (`api/v1/`)
- Upgraded to **FastAPI 0.109** with Pydantic v2 settings
- Replaced in-memory config with **YAML + environment override** pattern
- Refactored AI agents into **abstract base classes** with provider-specific implementations

### Security
- Structured exception handlers (no stack traces leaked to clients)
- File size validation middleware (413 on oversized uploads)
- CORS configurable per environment (restrictive fallback on failure)
- Sensitive files excluded from version control

## [1.0.0] - 2026-03-15

### Added
- Initial OCR Web UI with LM Studio integration
- Single-model support (LightOnOCR-2-1B)
- PDF and image processing
- Nuxt 3 frontend with drag-and-drop upload
- Docker Compose development stack
- Basic health check endpoint

---

[2.0.0]: https://github.com/user/doc-intelligence/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/user/doc-intelligence/releases/tag/v1.0.0
