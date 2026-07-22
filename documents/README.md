# M.DocAI (Dr.Vision) — Product Documentation

> Product Owner documentation set for the **M.DocAI** intelligent document processing platform (internal codename *Dr.Vision*).

This folder contains the product-level documentation derived from the codebase (`backend/` FastAPI service + `frontend/` Nuxt 3 SPA) and the original [`requirement.md`](../requirement.md).

## Documents

| # | Document | Purpose |
|---|----------|---------|
| 1 | [01-product-vision.md](01-product-vision.md) | Vision, problem statement, target users, value proposition |
| 2 | [02-prd.md](02-prd.md) | Product Requirements Document — goals, scope, features, non-functional requirements |
| 3 | [03-personas-and-use-cases.md](03-personas-and-use-cases.md) | User personas and end-to-end use cases |
| 4 | [04-user-stories.md](04-user-stories.md) | Epics and user stories with acceptance criteria |
| 5 | [05-functional-spec.md](05-functional-spec.md) | Detailed functional specification per capability |
| 6 | [06-api-reference.md](06-api-reference.md) | Backend REST API reference (integration/deploy) |
| 7 | [07-requirements-traceability.md](07-requirements-traceability.md) | Maps the 13 original requirements → build status (gap analysis) |
| 8 | [08-roadmap.md](08-roadmap.md) | Prioritized roadmap and backlog |

## Quick product summary

**M.DocAI** is an AI-powered **document digitalization** platform: it turns unstructured documents (PDF, PNG, JPG) into output that is both **human-readable** (layout-faithful text + DOCX) and **machine-readable** (structured JSON) in a single pass. It is **self-service** — usable no-code in the web app and, for developers, via a **REST API and client SDK** (SDK + self-service key issuance are the top roadmap items; see [08-roadmap.md](08-roadmap.md)).

It exposes five core capabilities and a visual workflow builder that chains them together:

1. **Parse / OCR** — extract text while preserving layout (Markdown/HTML), export to DOCX.
2. **Classify** — categorize documents against user-defined types.
3. **Extract** — pull structured fields via a schema (manual, from library, or AI-generated).
4. **Split** — divide mixed/multi-document files into sections or by document type.
5. **Document Journey** — a drag-and-drop workflow builder that orchestrates the above into end-to-end pipelines with conditional branching.

Processing quality/cost is controlled by a **three-tier model system** (Rapid / Normal / Advance) backed by AWS Bedrock (Claude), Google Gemini, POE, and local (LM Studio / Ollama / vLLM) providers.

## Key facts

- **Backend**: FastAPI (Python), default port `8082`. Agent-based architecture: `Input → API → Functions + Config → Agents → Output`.
- **Frontend**: Nuxt 3 / Vue 3 SPA, default dev port `3000`, calls backend at `API_BASE_URL` (default `http://localhost:8082`).
- **Async processing**: documents above `threshold_pages` (default 5) are processed as background jobs with polling.
- **Persistence**: workflows and run history are stored server-side (`workflow_store` / `run_store`) with a localStorage fallback in the browser.

> **Status legend used throughout:** ✅ Implemented · 🟡 Partial · 🔴 Not built (requirement gap).
