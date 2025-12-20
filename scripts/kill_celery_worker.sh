#!/bin/bash
# Helper script to kill Celery worker and its health server

echo "Finding Celery worker processes..."

# Find and kill Celery worker processes
WORKER_PIDS=$(ps aux | grep -E "celery.*worker|celery_worker_health" | grep -v grep | awk '{print $2}')
if [ ! -z "$WORKER_PIDS" ]; then
    echo "Killing Celery worker processes: $WORKER_PIDS"
    echo $WORKER_PIDS | xargs kill 2>/dev/null || true
else
    echo "No Celery worker processes found"
fi

# Kill any process using port 8080 (worker health server port)
PORT_PID=$(lsof -ti:8080 2>/dev/null)
if [ ! -z "$PORT_PID" ]; then
    echo "Killing process on port 8080 (PID: $PORT_PID)"
    kill $PORT_PID 2>/dev/null || true
fi

# Wait a moment for processes to terminate
sleep 1

# Force kill if still running
WORKER_PIDS=$(ps aux | grep -E "celery.*worker|celery_worker_health" | grep -v grep | awk '{print $2}')
if [ ! -z "$WORKER_PIDS" ]; then
    echo "Force killing remaining worker processes: $WORKER_PIDS"
    echo $WORKER_PIDS | xargs kill -9 2>/dev/null || true
fi

# Check if any processes are still running
REMAINING=$(ps aux | grep -E "celery.*worker|celery_worker_health" | grep -v grep | wc -l | tr -d ' ')
if [ "$REMAINING" -eq 0 ]; then
    echo "✅ All Celery worker processes terminated."
else
    echo "⚠️  Some processes may still be running. Check manually:"
    ps aux | grep -E "celery.*worker|celery_worker_health" | grep -v grep
fi
