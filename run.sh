#!/bin/bash

# Function to kill processes on exit
cleanup() {
    echo "Stopping servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID
    fi
    exit
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

export PYTHONPATH=$PYTHONPATH:$(pwd)

echo "Starting Backend on http://0.0.0.0:8000..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait a moment for backend to initialize
sleep 2

echo "Starting Frontend on http://0.0.0.0:5173..."
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

echo "Servers running. Press Ctrl+C to stop."
wait $FRONTEND_PID $BACKEND_PID
