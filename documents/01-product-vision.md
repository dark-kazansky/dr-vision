# Product Vision — M.DocAI

## 1. Vision statement

> **Digitalize every document — make it both human- and machine-readable.** **M.DocAI** turns any document — scanned, photographed, or born-digital — into clean, layout-faithful text a person can read *and* structured data a machine can consume, in seconds. It is a **self-service platform**: business teams do it in the web app without writing code, and engineering teams do the same through a **self-service SDK and API** — no tickets, no hand-holding.

## 2. Problem statement

Organizations (particularly in banking/finance — the deployment target is `mdocai.msb.com.vn`) receive huge volumes of documents in inconsistent formats: contracts, financial statements (BCTC), KYC packets, official correspondence, forms. Today these are:

- Read and re-keyed manually → slow, expensive, error-prone.
- Mixed into single PDFs (multiple document types in one file) that must be separated by hand.
- Impossible to search or feed into downstream systems because they are images, not data — **neither reliably human-readable (poor scans, mixed layouts) nor machine-readable (no structure a system can parse)**.

Generic OCR tools return raw text but lose layout, cannot classify or extract fields, and cannot be chained into a repeatable business process. And when developers want the same capability, they hit a wall: no self-service path — they must file requests and wait, instead of grabbing an SDK or key and integrating in an afternoon.

## 3. Solution

A single **digitalization platform** that produces output in two forms from the same pass:

- **Human-readable:** high-fidelity OCR/parsing that preserves layout (tables, headings) as Markdown/HTML and exports to DOCX — a clean document a person can read and edit.
- **Machine-readable:** schema-driven structured data (JSON) a downstream system can ingest directly.

Built on top of that, it combines:

- **AI classification** into caller-defined document types.
- **Schema-driven extraction** of structured fields (with AI-assisted schema authoring).
- **Smart splitting** of multi-document files.
- **A visual workflow builder** ("Document Journey") that composes these into end-to-end automations with conditional routing.
- **Tiered model selection** so users trade off speed vs. accuracy vs. cost per job.

Delivered as **self-service** through three surfaces of the same capability: an **interactive web app** (no code), a **REST API**, and a **client SDK** — pick the surface that fits, no onboarding gate.

## 4. Target users

| Segment | Who | Need |
|---------|-----|------|
| **Operations / back-office staff** | Non-technical document processors | Upload documents, get clean text/data, no coding |
| **Business analysts** | Define document types & extraction schemas | Configure classification rules and fields for their domain |
| **Automation owners** | Process designers | Build reusable multi-step "journeys" that run on document batches |
| **Developers / integrators** | Engineering teams | Call the platform from other systems via REST API |
| **Platform administrators** | IT/Ops | Configure model credentials (e.g., AWS Bedrock), monitor runs |

## 5. Value proposition

- **Digitalization, not just OCR**: every document becomes both a readable artifact and structured data in one pass.
- **Dual-readable output**: human-readable (layout-preserving Markdown/HTML + DOCX) and machine-readable (schema JSON) from the same request.
- **True self-service**: web app for business users, SDK + API for developers — provision, integrate, and run without a support ticket.
- **Speed**: seconds per document; batch and background processing for large files.
- **Accuracy control**: pick Rapid / Normal / Advance per task.
- **No-code automation**: drag-and-drop Document Journey builder.
- **Flexibility**: multi-provider model backend (Bedrock, Gemini, POE, local) with graceful fallback.
- **Embeddable**: every capability is an API endpoint and an SDK method.

## 6. Differentiators

1. **Dual-readable digitalization** — one pass yields both a human-readable document (layout-faithful + DOCX) and machine-readable structured data (JSON).
2. **Self-service across surfaces** — the same capability is reachable no-code (web), via REST API, and via a client SDK, without an onboarding gate.
3. **Journey orchestration with branching** — condition nodes route documents down different paths based on classification/extraction results.
4. **AI-generated schemas** — describe what you want in plain language and the system proposes an extraction schema.
5. **Two split modes** — split into semantic *sections* (header/body/table/footer/appendix) OR by *document type* boundaries within a mixed file.
6. **Tiered cost/quality** as a first-class product concept.

## 7. Success metrics (proposed)

| Metric | Target intent |
|--------|---------------|
| Documents processed / month | Adoption |
| Extraction field accuracy | Quality |
| Avg. processing time per page | Performance |
| % of documents handled by a saved Journey (vs. one-off) | Automation depth |
| API request volume | Integration adoption |
| Self-service integrations (keys issued / SDK installs) with no support ticket | Self-service adoption |
| % of output consumed machine-to-machine (structured JSON) vs. downloaded (DOCX) | Digitalization depth |
| Manual re-keying hours saved | Business ROI |

## 8. Scope boundaries

**In scope (built or planned):** OCR/parse, classify, extract, split, workflow orchestration, tiered models, background jobs, run history, API deploy snippets, model credential config.

**Committed but not yet built (the self-service backbone):** end-user authentication & IAM, self-service **API-key issuance/management**, and a downloadable **client SDK**. These are what turn "has an API" into "developers can self-serve" and are the top roadmap priority — see [08-roadmap.md](08-roadmap.md).

**Also planned:** a persistent Document Profile Library, formal audit trail, and the "Smart Sheet" capability. See [07-requirements-traceability.md](07-requirements-traceability.md).

> **Today vs. target for self-service:** the REST API is live and unauthenticated on a trusted network, and DeployDialog emits copyable snippets. Full self-service — where a developer signs in, issues their own scoped API key, and installs an SDK without involving an admin — depends on IAM (#6), API-key management (#2), and the SDK (#3).
