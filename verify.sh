#!/bin/bash
# verify.sh: Full Pipeline Verification for Doc Intelligence
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
echo "  DR VISION — FULL PIPELINE VERIFICATION"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════"

# Activate venv if exists
if [[ -d ".venv" ]]; then
    source .venv/bin/activate 2>/dev/null || true
fi

# GATE 1: Backend Lint
section "Gate 1: Backend Static Analysis"
cd backend
if command -v ruff >/dev/null 2>&1; then
    ruff check . 2>&1 && gate_pass "Backend lint (ruff): 0 errors" || gate_fail "Backend lint FAILED"
else
    echo -e "${YELLOW}⚠${NC}  ruff not installed, skipping backend lint"
fi
cd ..

# GATE 2: Backend Tests
section "Gate 2: Backend Unit Tests"
cd backend
pytest tests/ --tb=short -q 2>&1 && gate_pass "Backend tests: all pass" || gate_fail "Backend tests FAILED"
cd ..

# GATE 3: Frontend Type Check
section "Gate 3: Frontend Type Check"
cd frontend
npx vue-tsc --noEmit 2>&1 && gate_pass "Frontend TypeScript: 0 errors" || gate_fail "Frontend TypeScript FAILED"
cd ..

# GATE 4: Frontend Tests
section "Gate 4: Frontend Unit Tests"
cd frontend
npx vitest --run 2>&1 && gate_pass "Frontend tests: all pass" || gate_fail "Frontend tests FAILED"
cd ..

# GATE 5: Backend Smoke (requires running server)
section "Gate 5: Smoke Test"
if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    gate_pass "Backend /health responds"
elif curl -sf http://localhost:8000/ >/dev/null 2>&1; then
    gate_pass "Backend / responds"
else
    echo -e "${YELLOW}⚠${NC}  Backend not running, skipping smoke test (start with: cd backend && python main.py)"
fi

if curl -sf http://localhost:3000 >/dev/null 2>&1; then
    gate_pass "Frontend responds on :3000"
else
    echo -e "${YELLOW}⚠${NC}  Frontend not running, skipping (start with: cd frontend && npm run dev)"
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
