#!/bin/bash

echo "==================================="
echo "Backend Process Check"
echo "==================================="

# Find the backend process
BACKEND_PID=$(lsof -i :8082 | grep LISTEN | awk '{print $2}' | head -1)

if [ -z "$BACKEND_PID" ]; then
    echo "❌ Backend is not running on port 8082"
    echo ""
    echo "To start the backend:"
    echo "  cd backend"
    echo "  python main.py"
    exit 1
fi

echo "✅ Backend is running (PID: $BACKEND_PID)"
echo ""
echo "To see backend logs, find the terminal with this process:"
echo "  ps -p $BACKEND_PID -o command="
ps -p $BACKEND_PID -o command=
echo ""
echo "==================================="
echo "Testing Backend Endpoints"
echo "==================================="
echo ""

echo "1. Testing /test-logging endpoint..."
curl -s http://localhost:8082/test-logging | python3 -m json.tool
echo ""
echo "   👆 Check your backend terminal for log output!"
echo ""

echo "2. Checking available models..."
curl -s http://localhost:8082/models/check | python3 -m json.tool | head -30
echo ""

echo "==================================="
echo "Next Steps:"
echo "==================================="
echo "1. Find the terminal running: python main.py"
echo "2. That terminal will show all backend logs"
echo "3. Run your workflow and watch that terminal"
echo "==================================="
