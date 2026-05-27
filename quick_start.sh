#!/bin/bash

# Quick start script for Dr.Vision
# This script starts both backend and frontend servers

echo "🚀 Starting Dr.Vision..."
echo ""

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo "❌ Error: backend directory not found"
    echo "   Please run this script from the Dr.Vision root directory"
    exit 1
fi

# Check if frontend directory exists
if [ ! -d "frontend" ]; then
    echo "❌ Error: frontend directory not found"
    echo "   Please run this script from the Dr.Vision root directory"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🔧 Activating virtual environment..."
    source .venv/bin/activate
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo "📦 Starting backend server..."
cd backend
python main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Check if backend started successfully (port 8000)
if ! lsof -i :8000 >/dev/null 2>&1; then
    echo "❌ Backend failed to start"
    echo "   Check backend/main.py for errors"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo "✅ Backend started on http://localhost:8000"

# Start frontend
echo ""
echo "🎨 Starting frontend server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
echo "⏳ Waiting for frontend to start..."
sleep 5

# Check if frontend started successfully
if ! lsof -i :3000 >/dev/null 2>&1; then
    echo "❌ Frontend failed to start"
    echo "   Check frontend logs for errors"
    cleanup
    exit 1
fi

echo "✅ Frontend started on http://localhost:3000"
echo ""
echo "=================================="
echo "✅ Dr.Vision is ready!"
echo "=================================="
echo ""
echo "🌐 Open your browser to: http://localhost:3000"
echo ""
echo "📚 API Documentation: http://localhost:8000/docs"
echo "🏥 Health Check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for user to stop
wait
