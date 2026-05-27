# Subsystem 5: Session Lifecycle (Vòng đời phiên làm việc)

## Mục đích

Session lifecycle subsystem đảm bảo:

- **Mỗi session bắt đầu** từ known, healthy state
- **Mỗi session kết thúc** trong clean, resumable state

Không có subsystem này, các sessions là disconnected events. Với subsystem này, các sessions là **connected steps** trong một chuỗi liên tục.

## Full Lifecycle

### START PHASE

```
1. Đọc AGENTS.md
   → Nhắc lại invariants, commands, DoD

2. Chạy init.sh
   → Install deps, health check, start servers

3. Đọc claude-progress.md
   → Biết session cuối đã làm gì

4. Đọc feature_list.json
   → Biết feature nào pending, priority cao nhất

5. Kiểm tra git log
   → Xác nhận code state nhất quán với progress log
```

### SELECT PHASE

```
6. Chọn ĐÚNG MỘT feature (priority cao nhất, passes: false)

7. Ghi vào progress log: "Session bắt đầu. Sẽ làm feat-XXX."
```

### EXECUTE PHASE

```
8. Implement feature

9. Chạy verification (unit tests first, then full pipeline)

10. Nếu fail → fix và chạy lại verification

11. Khi verification pass → ghi lại evidence
```

### WRAP-UP PHASE

```
12. Cập nhật feature_list.json (passes: true, evidence)

13. Cập nhật claude-progress.md (session summary)

14. Ghi chú bất cứ thứ gì còn broken hoặc chưa verify

15. Git commit (chỉ khi verification pass hoàn toàn)

16. Viết handoff note cho session tiếp theo
```

## init.sh: The Gatekeeper

init.sh là script chạy ở đầu mỗi session. Nó là "gatekeeper" đảm bảo environment healthy trước khi agent bắt đầu làm bất cứ thứ gì.

### Nguyên tắc thiết kế init.sh

- Phải có exit code: **0** khi healthy, **non-zero** khi unhealthy
- Phải **idempotent**: chạy nhiều lần không gây side effects
- Phải **nhanh**: không nên mất > 60 giây
- Phải **toàn diện**: check tất cả critical dependencies

### Ví dụ init.sh

```bash
#!/bin/bash
set -euo pipefail

echo "=== HARNESS INIT [$(date)] ==="

# 1. Cài đặt dependencies (idempotent)
echo "[1/5] Installing dependencies..."
npm ci --silent
echo "  ✓ Dependencies OK"

# 2. Kiểm tra environment variables
echo "[2/5] Checking environment..."
: ${DATABASE_URL:? "DATABASE_URL not set"}
: ${API_KEY:? "API_KEY not set"}
echo "  ✓ Environment OK"

# 3. Database connectivity check
echo "[3/5] Database health..."
npx ts-node scripts/check-db.ts
echo "  ✓ Database OK"

# 4. Start servers
echo "[4/5] Starting servers..."
npm run dev &
DEV_PID=$!
echo $DEV_PID > .dev-server.pid
sleep 3

# 5. Smoke test
echo "[5/5] Smoke test..."
curl -sf http://localhost:3000/health >/dev/null || {
    echo "  ✗ Smoke test FAILED, app didn't start"
    kill $DEV_PID 2>/dev/null
    exit 1
}
echo "  ✓ Smoke test OK"

echo ""
echo "=== INIT COMPLETE ==="
echo "Environment is healthy. Agent can begin work."
echo "Next: Read claude-progress.md, then feature_list.json"
```

## Clean State Definition

"Clean state" không phải "perfect code". Nó là "**safely resumable**":

### CLEAN STATE = code suitable for merging to main branch

```
✓ No major bugs in implemented features
✓ All committed features have passing tests
✓ Code is orderly (no obvious mess, no half-done refactors)
✓ Documentation up-to-date (progress log, feature list)
✓ A developer (human or AI) could start new work without cleaning up first
```

### NOT CLEAN STATE:

```
✗ Tests failing
✗ TypeScript errors
✗ Half-implemented feature (logic started but not complete)
✗ No commit since last session (untracked changes)
✗ Progress log not updated
```

## Session Handoff

### Vấn đề

Mỗi session là một context mới. Agent không nhớ gì từ session trước.

### Giải pháp: Handoff Note trong agent-progress.md

```markdown
## Session #7 — 2026-05-19

### Completed
- Implemented feat-007 (user search)
- All verification gates L0-L5 PASS
- Committed: abc1234 "feat(search): add user search endpoint"

### Noted Issues (Out of Scope)
- [NOTED] feat-003 import: File >10MB gây UI freeze
  Tracked as: ISSUE-import-freeze-large-files

### Next Session Should
- Pick up feat-008 (export CSV) — next priority
- Or address ISSUE-import-freeze-large-files if critical

### Environment State
- Dev server running on :3000
- Database migrated to v15
- No pending untracked changes
```

## Anti-patterns

| Anti-pattern | Mô tả | Giải pháp |
|-------------|--------|-----------|
| No Startup | Bắt đầu code ngay không đọc context | Bắt buộc chạy init.sh + đọc progress |
| No Close | Kết thúc session không update state | Bắt buộc wrap-up phase |
| Skip Verify | Declare done mà không verify | Gate enforcement trong execute phase |
| Dirty Handoff | Để lại untracked changes, broken tests | Clean state check trước khi close |
| Context Loss | Session sau không biết session trước làm gì | Viết handoff note đầy đủ |
| Infinite Session | Session kéo dài không kết thúc | Set scope rõ ở select phase |
