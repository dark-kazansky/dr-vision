#!/bin/bash
# init.sh: Harness Session Initializer for Doc Intelligence
# Chạy đầu mỗi agent session. Must pass before any coding begins.
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

OK() { echo -e "${GREEN}[OK]${NC} $1"; }
FAIL() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }
WARN() { echo -e "${YELLOW}[WARN]${NC} $1"; }
INFO() { echo -e "${BLUE}[INFO]${NC} $1"; }

echo ""
echo "════════════════════════════════════════════"
echo "    DR VISION — HARNESS INIT"
echo "    $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════"
echo ""

# —— STEP 1: Prerequisites check ——————————————————————
INFO "Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || FAIL "python3 not found"
command -v node >/dev/null 2>&1 || FAIL "node not found"
command -v npm >/dev/null 2>&1 || FAIL "npm not found"
command -v docker >/dev/null 2>&1 || WARN "docker not found (optional for local dev)"
OK "Prerequisites: python3 $(python3 --version 2>&1 | cut -d' ' -f2), node $(node -v)"

# —— STEP 2: Backend Python environment ———————————————
INFO "Checking backend Python environment..."
if [[ -d ".venv" ]]; then
    source .venv/bin/activate 2>/dev/null || true
fi

cd backend
if python3 -c "import fastapi, uvicorn, pydantic_settings" 2>/dev/null; then
    OK "Backend dependencies installed"
else
    WARN "Missing backend deps, installing..."
    pip install -r requirements.txt --quiet || FAIL "pip install failed"
    OK "Backend dependencies installed"
fi
cd ..

# —— STEP 3: Frontend dependencies ————————————————————
INFO "Checking frontend dependencies..."
if [[ -d "frontend/node_modules" ]]; then
    OK "Frontend node_modules exists"
else
    WARN "Frontend node_modules missing, installing..."
    cd frontend && npm install --silent && cd ..
    OK "Frontend dependencies installed"
fi

# —— STEP 4: Infrastructure (Docker services) —————————
INFO "Checking Docker services..."
if command -v docker >/dev/null 2>&1; then
    if docker compose ps postgres 2>/dev/null | grep -q "running"; then
        OK "PostgreSQL running"
    else
        WARN "PostgreSQL not running. Start with: docker compose up -d postgres minio"
    fi

    if docker compose ps minio 2>/dev/null | grep -q "running"; then
        OK "MinIO running"
    else
        WARN "MinIO not running. Start with: docker compose up -d minio"
    fi
else
    WARN "Docker not available — skip infrastructure check"
fi

# —— STEP 5: Backend health check —————————————————————
INFO "Backend quick sanity check..."
cd backend
if python3 -c "from settings import settings; errors = settings.validate(); assert not errors, errors" 2>/dev/null; then
    OK "Backend settings valid"
else
    WARN "Backend settings validation has warnings (check config/settings.yaml)"
fi
cd ..

# —— STEP 6: Frontend type check (quick) ——————————————
INFO "Frontend quick sanity check..."
if [[ -d "frontend/node_modules" ]]; then
    cd frontend
    npx vue-tsc --noEmit 2>/dev/null && OK "Frontend TypeScript OK" || WARN "TypeScript errors found, check before declaring features done"
    cd ..
else
    WARN "Skipping frontend type check (no node_modules)"
fi

# —— SUMMARY ——————————————————————————————————————————
echo ""
echo "════════════════════════════════════════════"
echo -e "${GREEN}✓ INIT COMPLETE — Environment is healthy${NC}"
echo "════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Read: agent-progress.md (what happened last session)"
echo "  2. Read: feature_list.json (choose highest-priority pending feature)"
echo "  3. Work on ONE feature only"
echo ""
