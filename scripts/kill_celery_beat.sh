#!/bin/bash
# Helper script to kill Celery beat and its health server

echo "Finding Celery beat processes..."

# Find and kill Celery beat processes
BEAT_PIDS=$(ps aux | grep -E "celery.*beat|celery_beat_health" | grep -v grep | awk '{print $2}')
if [ ! -z "$BEAT_PIDS" ]; then
    echo "Killing Celery beat processes: $BEAT_PIDS"
    echo $BEAT_PIDS | xargs kill 2>/dev/null || true
else
    echo "No Celery beat processes found"
fi

# Kill any process using port 8081 (beat health server port)
PORT_PID=$(lsof -ti:8081 2>/dev/null)
if [ ! -z "$PORT_PID" ]; then
    echo "Killing process on port 8081 (PID: $PORT_PID)"
    kill $PORT_PID 2>/dev/null || true
fi

# Wait a moment for processes to terminate
sleep 1

# Force kill if still running
BEAT_PIDS=$(ps aux | grep -E "celery.*beat|celery_beat_health" | grep -v grep | awk '{print $2}')
if [ ! -z "$BEAT_PIDS" ]; then
    echo "Force killing remaining beat processes: $BEAT_PIDS"
    echo $BEAT_PIDS | xargs kill -9 2>/dev/null || true
fi

# Check if any processes are still running
REMAINING=$(ps aux | grep -E "celery.*beat|celery_beat_health" | grep -v grep | wc -l | tr -d ' ')
if [ "$REMAINING" -eq 0 ]; then
    echo "✅ All Celery beat processes terminated."
else
    echo "⚠️  Some processes may still be running. Check manually:"
    ps aux | grep -E "celery.*beat|celery_beat_health" | grep -v grep
fi
