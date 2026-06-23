#!/bin/bash
# quick_start.sh: Start Doc Intelligence (backend + frontend)
# Convenience script for local development.
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping servers...${NC}"
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "════════════════════════════════════════════"
echo "  DR VISION — QUICK START"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════"
echo ""

# --- Validate directory structure ---
[[ -d "backend" ]]  || { echo -e "${RED}[FAIL]${NC} backend/ directory not found"; exit 1; }
[[ -d "frontend" ]] || { echo -e "${RED}[FAIL]${NC} frontend/ directory not found"; exit 1; }

# --- Activate virtual environment if available ---
if [[ -d ".venv" ]]; then
    echo -e "${BLUE}[INFO]${NC} Activating .venv"
    source .venv/bin/activate
fi

# --- Start backend ---
echo -e "${BLUE}[INFO]${NC} Starting backend server..."
cd backend
python main.py &
BACKEND_PID=$!
cd ..

echo -e "${BLUE}[INFO]${NC} Waiting for backend to start..."
sleep 5

if ! lsof -i :8000 >/dev/null 2>&1; then
    echo -e "${RED}[FAIL]${NC} Backend failed to start on :8000"
    kill "$BACKEND_PID" 2>/dev/null || true
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Backend running on http://localhost:8000"

# --- Start frontend ---
echo -e "${BLUE}[INFO]${NC} Starting frontend server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "${BLUE}[INFO]${NC} Waiting for frontend to start..."
sleep 5

if ! lsof -i :3000 >/dev/null 2>&1; then
    echo -e "${RED}[FAIL]${NC} Frontend failed to start on :3000"
    cleanup
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Frontend running on http://localhost:3000"

# --- Ready ---
echo ""
echo "════════════════════════════════════════════"
echo -e "${GREEN}  DR VISION IS READY${NC}"
echo "════════════════════════════════════════════"
echo ""
echo "  App:    http://localhost:3000"
echo "  API:    http://localhost:8000/docs"
echo "  Health: http://localhost:8000/health"
echo ""
echo "  Press Ctrl+C to stop both servers"
echo ""

wait
