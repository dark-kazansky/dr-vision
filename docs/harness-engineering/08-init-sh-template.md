# init.sh: Script Production-grade

## Template

```bash
#!/bin/bash
# init.sh: Harness Session Initializer
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
echo "    HARNESS INIT, $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════"
echo ""

# —— STEP 1: Prerequisites check ——————————————————————
INFO "Checking prerequisites..."
command -v node >/dev/null 2>&1 || FAIL "node not found. Install Node.js >= 20"
command -v npm >/dev/null 2>&1 || FAIL "npm not found"
NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
[[ $NODE_VERSION -ge 20 ]] || FAIL "Node.js >= 20 required (got $(node -v))"
OK "Node.js $(node -v)"

# —— STEP 2: Install dependencies ————————————————————
INFO "Installing dependencies..."
if npm ci --silent 2>/dev/null; then
    OK "Dependencies installed (npm ci)"
else
    WARN "npm ci failed, trying npm install..."
    npm install --silent || FAIL "npm install failed"
    OK "Dependencies installed (npm install)"
fi

# —— STEP 3: Environment validation ——————————————————
INFO "Validating environment..."
if [[ -f ".env.local" ]]; then
    source .env.local
fi
# Check required vars (add your variables here)
# : ${DATABASE_URL:? "Missing DATABASE_URL in .env.local"}
OK "Environment validated"

# —— STEP 4: Quick sanity: TypeScript compilation ————
INFO "TypeScript sanity check..."
npx tsc --noEmit --skipLibCheck 2>/dev/null || WARN "TypeScript errors found, check before declaring features done"

# —— STEP 5: Start services ——————————————————————————
INFO "Starting development server..."

# Kill any existing dev server
if [[ -f .dev-server.pid ]]; then
    OLD_PID=$(cat .dev-server.pid)
    kill $OLD_PID 2>/dev/null || true
fi

npm run dev > artifacts/logs/dev-server.log 2>&1 &
DEV_PID=$!
echo $DEV_PID > .dev-server.pid

# Wait for server with timeout
MAX_WAIT=30
WAITED=0
until curl -sf http://localhost:3000 >/dev/null 2>&1; do
    if [[ $WAITED -ge $MAX_WAIT ]]; then
        FAIL "Server didn't start in ${MAX_WAIT}s. Check artifacts/logs/dev-server.log"
    fi
    sleep 1
    ((WAITED++))
done
OK "Dev server running (PID: $DEV_PID)"

# —— STEP 6: Smoke test ——————————————————————————————
INFO "Running smoke test..."
npm run test:smoke --silent || FAIL "Smoke tests failed, investigate before coding"
OK "Smoke tests pass"

# —— SUMMARY ——————————————————————————————————————————
echo ""
echo "════════════════════════════════════════════"
echo -e "${GREEN}✓ INIT COMPLETE, Environment is healthy${NC}"
echo "════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Read: claude-progress.md (what happened last session)"
echo "  2. Read: feature_list.json (choose highest-priority pending feature)"
echo "  3. Work on ONE feature only"
echo ""
```

## Nguyên tắc thiết kế

| Nguyên tắc | Mô tả |
|-----------|-------|
| Exit code 0/non-zero | 0 = healthy, non-zero = unhealthy. Agent DỪNG nếu non-zero |
| Idempotent | Chạy nhiều lần không gây side effects |
| Nhanh | Không nên mất > 60 giây |
| Toàn diện | Check tất cả critical dependencies |
| Informative | Output rõ ràng, biết ngay step nào fail |

## Tùy chỉnh cho project của bạn

### Thêm database check

```bash
# —— STEP X: Database connectivity ————————————————————
INFO "Checking database..."
npx ts-node scripts/check-db.ts || FAIL "Database unreachable"
OK "Database connected"
```

### Thêm Docker services

```bash
# —— STEP X: Docker services ——————————————————————————
INFO "Starting Docker services..."
docker compose up -d --wait || FAIL "Docker services failed to start"
OK "Docker services running"
```

### Cho Python project

```bash
# —— STEP 2: Python environment ——————————————————————
INFO "Setting up Python environment..."
if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt --quiet || FAIL "pip install failed"
OK "Python environment ready"
```
