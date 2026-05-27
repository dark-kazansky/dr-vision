# verify.sh: Full Pipeline Verification

## Template

```bash
#!/bin/bash
# verify.sh: Full Pipeline Verification
# Chạy trước khi declare bất kỳ feature nào done.
# Exit 0 = tất cả gates pass. Exit 1 = có gate fail.

set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

PASS=0; FAIL_COUNT=0
START_TIME=$(date +%s)

gate_pass() { echo -e "${GREEN}✓${NC} $1"; ((PASS++)); }
gate_fail() { echo -e "${RED}✗${NC} $1"; ((FAIL_COUNT++)); }
section() { echo ""; echo "—— $1 ————————————————————————————————"; }

echo "════════════════════════════════════════════"
echo "  FULL PIPELINE VERIFICATION"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════"

# GATE 1: Lint
section "Gate 1: Static Analysis"
npm run lint --silent 2>&1 && gate_pass "Lint (0 errors)" || gate_fail "Lint FAILED"

npm run type-check --silent 2>&1 && gate_pass "TypeScript (0 errors)" || gate_fail "TypeScript FAILED"

# GATE 2: Unit Tests
section "Gate 2: Unit Tests"
RESULT=$(npm test --silent 2>&1)
echo "$RESULT" | tail -3
echo "$RESULT" | grep -q "✗ \|failing\|FAIL" && gate_fail "Unit Tests FAILED" || gate_pass "Unit Tests (all pass)"

# GATE 3: Build
section "Gate 3: Build"
npm run build --silent 2>&1 && gate_pass "Build (success)" || gate_fail "Build FAILED"

# GATE 4: Smoke
section "Gate 4: Smoke Tests"
npm run test:smoke --silent 2>&1 && gate_pass "Smoke Tests" || gate_fail "Smoke Tests FAILED"

# GATE 5: E2E (optional, requires running app)
section "Gate 5: E2E Tests"
if curl -sf http://localhost:3000 >/dev/null 2>&1; then
    npm run test:e2e --silent 2>&1 && gate_pass "E2E Tests" || gate_fail "E2E Tests FAILED"
else
    echo -e "${YELLOW}${NC}  E2E skipped (app not running, run init.sh first)"
fi

# SUMMARY
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo ""
echo "════════════════════════════════════════════"
if [[ $FAIL_COUNT -eq 0 ]]; then
    echo -e "${GREEN}✓ ALL GATES PASSED ($PASS checks in ${DURATION}s)${NC}"
    echo "Safe to: mark features done, commit code"
    exit 0
else
    echo -e "${RED}✗ $FAIL_COUNT GATE(S) FAILED${NC}"
    echo "Do NOT mark features done or commit until fixed"
    exit 1
fi
```

## Cách sử dụng

### Khi nào chạy verify.sh?

| Tình huống | Chạy verify.sh? |
|-----------|----------------|
| Trước khi mark feature done | ✓ Bắt buộc |
| Trước khi commit | ✓ Bắt buộc |
| Sau khi fix bug | ✓ Bắt buộc |
| Giữa session (quick check) | Optional (có thể chạy từng gate riêng) |

### Đọc kết quả

```
════════════════════════════════════════════
  FULL PIPELINE VERIFICATION
  2025-04-06 10:30:00
════════════════════════════════════════════

—— Gate 1: Static Analysis ————————————————
✓ Lint (0 errors)
✓ TypeScript (0 errors)

—— Gate 2: Unit Tests ————————————————————
✓ Unit Tests (all pass)

—— Gate 3: Build ——————————————————————————
✓ Build (success)

—— Gate 4: Smoke Tests ————————————————————
✓ Smoke Tests

—— Gate 5: E2E Tests ——————————————————————
✓ E2E Tests

════════════════════════════════════════════
✓ ALL GATES PASSED (7 checks in 45s)
Safe to: mark features done, commit code
```

### Khi có gate fail

```
════════════════════════════════════════════
✗ 1 GATE(S) FAILED
Do NOT mark features done or commit until fixed
```

→ Fix lỗi → Chạy lại `./verify.sh` → Lặp lại cho đến khi ALL PASS

## Tùy chỉnh cho project

### Thêm gate cho Python

```bash
# GATE X: Python Tests
section "Gate X: Python Tests"
pytest tests/ --quiet 2>&1 && gate_pass "Pytest (all pass)" || gate_fail "Pytest FAILED"
```

### Thêm gate cho Docker

```bash
# GATE X: Container Build
section "Gate X: Container Build"
docker build -t myapp:test . 2>&1 && gate_pass "Docker build" || gate_fail "Docker build FAILED"
```

### Thêm gate cho Security

```bash
# GATE X: Security Audit
section "Gate X: Security Audit"
npm audit --production 2>&1 && gate_pass "No vulnerabilities" || gate_fail "Security vulnerabilities found"
```
