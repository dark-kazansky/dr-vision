# Roadmap & Backlog — M.DocAI

Sequenced from the gap analysis in [07-requirements-traceability.md](07-requirements-traceability.md). Prioritization balances **enterprise readiness** (security/compliance for the MSB banking deployment) against **completing the product promise**.

## Guiding principle
Core document **digitalization** (parse to human- and machine-readable output, classify, extract, split, journey, tiers) is **done and usable today** — no-code in the web app and via the live REST API. The roadmap focuses on completing the **self-service developer backbone** (sign in → issue your own scoped API key → install an SDK, no admin in the loop), then making profiles reusable and the product complete.

---

## Now — Self-service developer backbone (Q-next)

The three items that turn the live API into a **self-service** offering — a developer signs in, issues their own scoped key, and installs an SDK without an admin.

| Priority | Item | Req | Why | Rough scope |
|:---:|------|:---:|-----|------|
| P0 | **Login & IAM** | #6 | Self-service prerequisite: identifies who is provisioning; unblocks self-issued API keys & audit attribution | Auth provider integration (SSO/OIDC likely for MSB), sessions, roles, endpoint guards |
| P0 | **Self-service API key management** | #2, #3 | Lets developers issue/revoke/scope their own keys and integrate without a support ticket; secures public endpoints | Self-serve key issue/revoke/scope UI + API, per-key rate limits, key auth middleware |
| P0 | **Client SDK (moved up)** | #3 | The third leg of self-service — a developer installs a package and calls a method, not raw cURL | Python/JS SDK wrapping REST, key-based auth, published package, quickstart docs |
| P1 | **Audit trail** | #4 | Banking compliance; who processed what, when (self-service makes attribution essential) | Durable, append-only, user-attributed event log + retention/export |

## Next — Complete the product promise

| Priority | Item | Req | Why | Rough scope |
|:---:|------|:---:|-----|------|
| P1 | **Document Profile Library** | #5, #9, #11 | Reusable profiles (type + schema + rules + categories) across all capabilities; completes "schema from library" | Server-side store + CRUD API + UI picker in Classify/Extract/Split/Journey |
| P1 | **Split auto-naming & per-document export** | #10 | Finishes "Smart Split" — separated files that are named and downloadable | Post-split file generation, naming rules, download endpoints |
| P2 | **System document-type taxonomy** | #11 | Built-in "system list" of common types so users don't start from scratch | Canonical server-side taxonomy + merge with user list |
| P2 | **Journey: Validate & User-Script nodes** | #13 | Nodes already visible in UI but disabled | Backend executors + sandboxing for user scripts, validation rules |

## Later — Scale & developer experience

| Priority | Item | Req | Why | Rough scope |
|:---:|------|:---:|-----|------|
| P2 | **Job scheduler / queue hardening** | #1 | Move from in-process threads to a real queue for scale & retries | Queue backend (e.g., Celery/RQ), retry policy, worker scaling |
| P3 | **Smart Sheet** | #12 | Region-aware spreadsheet digitalization → typed Parquet + metadata (**now specified** — see [05-functional-spec.md §12](05-functional-spec.md)) | Region detection, per-region extraction, Parquet serialization, region/sheet metadata, Journey node |
| P3 | **Templated parse output** | #8 | Parse into a fixed template layout distinct from extraction | Template model + mapping UI |

---

## Backlog / smaller improvements
- Increase file size limit / add more file types (currently 10 MB, PDF/PNG/JPG/JPEG).
- FeedbackDialog currently only logs client-side — wire to a backend endpoint / ticketing.
- Unify the DeployDialog display base URL with actual runtime `apiBaseUrl` (currently hard-coded `mdocai.msb.com.vn:8000`).
- Consolidate `/ocr` legacy alias and error-type contract with the newer `/parse` response shape.
- Surface tier-model transparency (which model ran) in results for auditability.
- Batch/folder ingestion beyond current multi-file selection.

---

## Suggested release themes

- **R1 — "Self-Service & Secure"**: Login/IAM + self-service API keys + client SDK + audit trail. Turns the live API into a self-service offering deployable beyond a trusted network.
- **R2 — "Reusable"**: Document Profile Library + system taxonomy + split export. Turns one-off configs into shared assets.
- **R3 — "Extensible"**: Validate/User-Script nodes + queue hardening. Grows the automation & integration surface.
- **R4 — "Smart Sheet"**: region-aware spreadsheet digitalization to typed Parquet + metadata (now specified).

---

## Open questions for stakeholders
1. **Auth model:** SSO/OIDC via MSB identity, or standalone accounts? (Drives #6/#2 design.)
2. **Smart Sheet (#12):** behavior now defined (region detection → per-region Parquet + metadata; see [05-functional-spec.md §12](05-functional-spec.md)). Remaining build questions: accepted input formats (native XLSX vs. OCR'd spreadsheet images), detection model vs. heuristic, Parquet delivery (per-file vs. bundled), and output retention.
3. **Deployment topology:** single-tenant internal vs. multi-tenant? (Affects IAM, rate limits, data isolation.)
4. **Data retention:** how long should `data/` outputs, jobs, and audit logs persist?
5. **Compliance scope:** which regulations apply to the audit trail (#4)?
