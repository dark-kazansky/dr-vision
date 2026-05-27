# AGENTS.md: Dr Vision
**Version:** 1.0 | **Last Updated:** 2026-05-19 | **Project Stage:** Active Development

## 🚀 BẮT ĐẦU MỖI SESSION (đọc trước, làm sau)

**PHẢI LÀM theo thứ tự này:**
1. `./init.sh`, setup môi trường và health check
2. `cat agent-progress.md | tail -50`, session cuối làm gì?
3. `cat feature_list.json | python3 -c "import json,sys; f=json.load(sys.stdin); [print(f['id'],f['description']) for f in f['features'] if not f['passes']]"`, feature pending
4. Chọn feature priority cao nhất → làm ĐÚNG feature đó

**DỪNG NẾU init.sh fail**: Fix môi trường trước khi làm bất cứ thứ gì.

## 📋 PROJECT OVERVIEW

**Mục đích:** OCR Web UI — Hệ thống nhận dạng ký tự quang học, xử lý ảnh/PDF qua nhiều AI models, tích hợp banking data mining.

**Tech Stack:**
- Backend: FastAPI 0.109 + Python 3.11 + Pydantic Settings
- Frontend: Nuxt 4 + Vue 3 + TypeScript + TailwindCSS
- Database: PostgreSQL 16 (port 5433) + MinIO (object storage)
- AI Providers: LM Studio (local), Google Gemini, AWS Bedrock, Ollama
- Testing: Pytest + Hypothesis (backend), Vitest + fast-check (frontend)
- Infra: Docker Compose, Kubernetes

**Key directories:**
```
backend/   ← FastAPI app (server.py = entry)
  agents/  ← Multi-provider AI agents (factory pattern)
  api/     ← Versioned REST API (v1/)
  services/← Business logic
  storage/ ← PostgreSQL banking repository
  config/  ← YAML-based model configuration
frontend/  ← Nuxt 4 app
  app/     ← Pages, components, composables
```

**Architecture:** Xem `docs/existing_features.md`

## 🚫 INVARIANTS (KHÔNG BAO GIỜ VI PHẠM)

1. **ONE FEATURE/SESSION**: Không implement nhiều hơn 1 feature trong 1 session
2. **NO FALSE DONE**: Không mark `passes: true` khi chưa chạy verification
3. **NO BROKEN COMMITS**: Không commit khi tests fail hoặc lint errors
4. **NO TEST DELETION**: Không xóa test steps từ feature_list.json
5. **NO SILENT SCOPE CREEP**: Phát hiện bug ngoài scope → Stop-and-Note
6. **NO SKIP INIT**: Không bắt đầu coding trước khi init.sh pass

## ✅ DEFINITION OF DONE

**Technical Gates:**
- Backend: `cd backend && ruff check .` → 0 errors
- Backend: `cd backend && pytest` → tất cả pass
- Frontend: `cd frontend && npx vue-tsc --noEmit` → 0 errors
- Frontend: `cd frontend && npx vitest --run` → tất cả pass

**Functional Gates:**
- Chạy TẤT CẢ test_steps trong feature_list.json
- Edge cases: empty state, error state, loading state đều handle
- Smoke test: app starts, basic endpoints respond

**State Update Gates:**
- feature_list.json: `passes: true`, `evidence` filled
- agent-progress.md: session entry added
- Git committed: `feat(scope): description`

## 🔧 COMMANDS

```bash
# Startup
./init.sh

# Backend
cd backend && python main.py              # Run server (port 8000)
cd backend && pytest                      # Unit tests
cd backend && pytest tests/ -x --tb=short # Quick test
cd backend && ruff check .                # Lint

# Frontend
cd frontend && npm run dev                # Dev server (port 3000)
cd frontend && npx vitest --run           # Unit tests
cd frontend && npx vue-tsc --noEmit       # Type check

# Infrastructure
docker compose up -d postgres minio       # Start DB + storage
docker compose up                         # Full stack

# Full verification
./verify.sh
```

## 📚 TÀI LIỆU CHI TIẾT

| Khi nào cần | Đọc file |
|-------------|----------|
| Hiểu features hiện có | docs/existing_features.md |
| Banking data mining | docs/banking-data-mining/ |
| Harness methodology | docs/harness-engineering/ |

## 🔥 TROUBLESHOOTING NHANH

**"PostgreSQL connection refused"**
→ `docker compose up -d postgres` → wait 5s → retry

**"Backend import error"**
→ `cd backend && pip install -r requirements.txt`

**"Frontend build fail"**
→ `cd frontend && rm -rf node_modules .nuxt && npm install`

**"Port already in use"**
→ `lsof -ti:8000 | xargs kill -9` hoặc `lsof -ti:3000 | xargs kill -9`

---
*Cập nhật AGENTS.md khi: thêm command mới, thay đổi tech stack, cập nhật invariants*
