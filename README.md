# Doc Intelligence — Document Intelligence Platform

AI-powered document processing platform for banking operations. Provides OCR, structured data extraction, document classification, and multi-document splitting through a unified REST API.

**Version:** 2.0.0 | **Stack:** FastAPI + Nuxt 4 + PostgreSQL + Multi-Provider AI

---

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────┐
│   Frontend      │     │          Backend (FastAPI)                │
│   Nuxt 4 + Vue  │────▶│  API → Services → Components → Agents   │
│   TailwindCSS   │     │                                          │
└─────────────────┘     │  Providers: Gemini │ Bedrock │ LM Studio │
                        │             Ollama │ vLLM    │ POE       │
                        └──────────┬───────────────────────────────┘
                                   │
                        ┌──────────▼───────────────────────────────┐
                        │  PostgreSQL 16  │  MinIO Object Storage   │
                        └──────────────────────────────────────────┘
```

## Key Capabilities

| Feature | Description |
|---------|-------------|
| **Parse (OCR)** | Extract text from images, PDFs, DOCX — sync or async |
| **Extract** | Schema-based structured data extraction with AI |
| **Split** | Categorize multi-document bundles by page range |
| **Classify** | Document type classification with confidence scoring |
| **Workflow** | Multi-step pipelines (OCR → Classify → Extract → Validate) |
| **Banking Analytics** | Transaction categorization and statement analysis |

## Quick Start

```bash
# 1. Start infrastructure
docker compose up -d postgres minio

# 2. Backend
cd backend
cp .env.example .env          # Configure API keys
pip install -r requirements.txt
python main.py                 # http://localhost:8000

# 3. Frontend
cd frontend
npm install
npm run dev                    # http://localhost:3000
```

**Full stack (Docker):**
```bash
docker compose up
```

## Project Structure

```
doc-intelligence/
├── backend/                    FastAPI application
│   ├── api/v1/                 REST endpoints (versioned)
│   ├── services/               Business logic layer
│   ├── components/             AI components (Parser, Extractor, Splitter)
│   ├── agents/                 Multi-provider AI agents (Factory pattern)
│   ├── core/                   Middleware, schemas, exceptions, utilities
│   ├── storage/                PostgreSQL repositories
│   ├── config/                 YAML config + tier routing
│   └── tests/                  Unit & integration tests (pytest)
├── frontend/                   Nuxt 4 + Vue 3 + TypeScript + TailwindCSS
│   ├── app/pages/              Page routes
│   ├── app/components/         Vue components
│   └── app/composables/        Shared logic (API client, state)
├── docs/                       Architecture & API documentation
│   ├── api-specification.md    Full API reference
│   ├── sequence-diagram.md     BPM integration flow
│   └── existing_features.md    Feature inventory
├── k8s/                        Kubernetes deployment manifests
├── .postman/                   Postman collection + environment (56 requests)
├── docker-compose.yml          Local development stack
└── CHANGELOG.md                Version history
```

## API Endpoints

| Group | Endpoints | Description |
|-------|-----------|-------------|
| Parse | `POST /parse`, `POST /ocr` | OCR text extraction |
| Extract | `POST /extract`, `POST /extract-text`, `POST /generate-schema` | Structured extraction |
| Split | `POST /split` | Document categorization |
| Jobs | `GET/DELETE /api/v1/jobs/{id}` | Async job management |
| Workflows | `CRUD /api/v1/workflows` | Pipeline management |
| Observability | `/api/v1/observability/*` | Metrics, timeline, audit |

Full specification: [`docs/api-specification.md`](docs/api-specification.md)

## Testing

```bash
# Backend unit tests
cd backend && pytest

# Backend lint
cd backend && ruff check .

# Frontend type check
cd frontend && npx vue-tsc --noEmit

# Frontend unit tests
cd frontend && npx vitest --run

# Postman collection (requires newman)
npx newman run .postman/doc-intelligence-collection.json -e .postman/doc-intelligence-environment.json
```

## Configuration

Backend reads from `backend/config/settings.yaml` with env variable overrides:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://...localhost:5433/drvision` |
| `GOOGLE_STUDIO_API_KEY` | Gemini API key | — |
| `BEDROCK_REGION` | AWS region for Claude | `ap-southeast-2` |
| `MAX_FILE_SIZE_MB` | Upload size limit | `10` |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | Rate limit | `30` |

See `backend/.env.example` for all options.

## Deployment

| Target | Command | Notes |
|--------|---------|-------|
| Local | `docker compose up` | All services on localhost |
| Kubernetes | `kubectl apply -f k8s/` | PostgreSQL, MinIO, Backend, Frontend |
| Production | CI/CD pipeline | Configurable via env vars |

## Documentation

| Document | Content |
|----------|---------|
| [`docs/api-specification.md`](docs/api-specification.md) | Complete API reference for SA review |
| [`docs/sequence-diagram.md`](docs/sequence-diagram.md) | BPM ↔ AI Server integration flow |
| [`docs/existing_features.md`](docs/existing_features.md) | Feature inventory |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history |
| `/docs` endpoint | Interactive Swagger UI |
| `/redoc` endpoint | ReDoc API documentation |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI 0.109, Pydantic v2 |
| Frontend | Nuxt 4, Vue 3, TypeScript, TailwindCSS |
| Database | PostgreSQL 16 (async via asyncpg) |
| Storage | MinIO (S3-compatible) |
| AI | Google Gemini, AWS Bedrock (Claude), LM Studio, Ollama, vLLM |
| Testing | pytest + hypothesis (BE), vitest + fast-check (FE) |
| Infra | Docker Compose, Kubernetes |

## License

Internal use — Banking AI Platform Team.
