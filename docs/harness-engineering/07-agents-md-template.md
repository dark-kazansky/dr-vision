# AGENTS.md: Bản thiết kế đầy đủ

AGENTS.md là file quan trọng nhất trong toàn bộ harness. Đây là template production-grade với giải thích:

## Template

```markdown
# AGENTS.md: [Tên Project]
**Version:** 2.1 | **Last Updated:** 2025-04-06 | **Project Stage:** Alpha

## 🚀 BẮT ĐẦU MỖI SESSION (đọc trước, làm sau)

**PHẢI LÀM theo thứ tự này:**
1. `./init.sh`, setup môi trường và health check
2. `cat claude-progress.md | tail -50`, session cuối làm gì?
3. `cat feature_list.json | python3 -c "import json,sys; f=json.load(sys.stdin); [print(f['id'],f['description']) for f in f['features'] if not f['passes']]"`, feature pending
4. Chọn feature priority cao nhất → làm ĐÚNG feature đó

**DỪNG NẾU init.sh fail**: Fix môi trường trước khi làm bất cứ thứ gì.

## 📋 PROJECT OVERVIEW

**Mục đích:** Knowledge Base Desktop App, cho phép user import tài liệu và tìm kiếm với AI

**Tech Stack:**
- Runtime: Electron 28 + Node.js 20
- Frontend: React 18 + TypeScript 5.3
- Styling: Tailwind CSS 3.4
- Database: SQLite (better-sqlite3) cho metadata, ChromaDB cho vectors
- Testing: Vitest (unit) + Playwright (E2E)

**Architecture sơ đồ:** Xem `docs/architecture.md`

**Key directories:**

src/ ├── main/      ← Electron main process
     ├── renderer/  ← React frontend
     ├── preload/   ← IPC bridge
     └── shared/    ← Shared types & utils

## 🚫 INVARIANTS (KHÔNG BAO GIỜ VI PHẠM)

Những quy tắc này là absolute. Không có exception:

1. **ONE FEATURE/SESSION**: Không implement nhiều hơn 1 feature trong 1 session
2. **NO FALSE DONE**: Không mark `passes: true` khi chưa chạy E2E test steps
3. **NO BROKEN COMMITS**: Không commit khi `npm test` hoặc `npm run lint` fail
4. **NO TEST DELETION**: Không xóa test steps từ feature_list.json
5. **NO SILENT SCOPE CREEP**: Phát hiện bug ngoài scope → dùng Stop-and-Note, không tự sửa
6. **NO SKIP INIT**: Không bắt đầu coding trước khi init.sh pass

## ✅ DEFINITION OF DONE

Một feature là DONE khi VÀ CHỈ KHI tất cả items sau checked:

**Technical Gates:**
- `npm run lint` → exit code 0, 0 errors
- `npm run type-check` → exit code 0, 0 errors
- `npm test` → tất cả tests pass
- `npm run build` → build success

**Functional Gates:**
- Chạy TẤT CẢ test_steps trong feature_list.json cho feature này
- Mỗi step pass thủ công trong app thực sự
- Edge cases: empty state, error state, loading state đều handle
- Không có broken features từ trước (smoke test pass)

**State Update Gates:**
- feature_list.json: `passes: true`, `evidence` filled
- claude-progress.md: session entry added
- Git committed với format: `feat(scope): description`

## 🔧 COMMANDS

```bash
# Startup (chạy đầu mỗi session)
./init.sh

# Verification (chạy theo thứ tự)
npm run lint            # Static analysis
npm run type-check      # TypeScript check
npm test                # Unit tests
npm run test:smoke      # Smoke tests
npm run test:e2e        # E2E tests (cần app đang chạy)
./verify.sh             # Chạy tất cả theo thứ tự

# Development
npm run dev             # Start Electron app (development)
npm run dev:renderer    # Chỉ start React dev server

# Build
npm run build           # Production build
```

## 📚 TÀI LIỆU CHI TIẾT

Đọc khi cần, không bắt buộc đọc mỗi session:

| Khi nào cần | Đọc file |
|-------------|----------|
| Hiểu system design | docs/architecture.md |
| Implement API | docs/api-contracts.md |
| Viết tests | docs/testing-guide.md |
| Gặp lỗi lạ | docs/troubleshooting.md |
| Hiểu tại sao dùng SQLite | docs/decisions/001-database.md |

## 🔥 TROUBLESHOOTING NHANH

**"init.sh fail: npm ci error"**
→ Xóa node_modules: `rm -rf node_modules && npm ci`

**"App không start sau init"**
→ Check port 3000: `lsof -ti:3000 | xargs kill -9` → Chạy lại init.sh

**"TypeScript errors không liên quan đến feature tôi đang làm"**
→ Check git log để biết ai/khi nào tạo ra lỗi → Fix lỗi đó trước (ngay cả khi ngoài scope) → Ghi chú trong progress log

---

*Cập nhật AGENTS.md khi: thêm command mới, thay đổi tech stack, cập nhật invariants*
*Không cập nhật AGENTS.md khi: thêm feature thông thường*
```

## Nguyên tắc thiết kế AGENTS.md

1. **Dưới 200 dòng** — Đủ ngắn để agent đọc toàn bộ mỗi session
2. **Actionable** — Mỗi section có hành động cụ thể
3. **Ordered** — Startup procedure theo thứ tự rõ ràng
4. **Invariants rõ ràng** — Không mơ hồ, không exception
5. **Progressive disclosure** — Link đến docs/ cho chi tiết, không inline
6. **Troubleshooting** — Giải quyết nhanh các vấn đề phổ biến
