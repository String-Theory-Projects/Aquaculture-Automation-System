#!/bin/bash
# Wrapper script to start Celery worker with health check server
# This allows Railway to monitor the health endpoint while Celery worker runs

set -e

# Change to project root directory (parent of scripts/)
cd "$(dirname "$0")/.." || exit 1

# Function to cleanup on exit
cleanup() {
    if [ ! -z "$HEALTH_PID" ]; then
        kill $HEALTH_PID 2>/dev/null || true
        wait $HEALTH_PID 2>/dev/null || true
    fi
}

trap cleanup EXIT INT TERM

# Determine Python executable (prefer venv, fallback to system python3)
if [ -f .venv/bin/python ]; then
    PYTHON_CMD=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

# Set default port for worker health server (8080)
# On Railway, PORT env var will override this
export PORT=${PORT:-8080}

# Start health server in background
# Redirect stderr to a log file for debugging, but don't fail if it errors initially
$PYTHON_CMD manage.py celery_worker_health > /tmp/celery_worker_health.log 2>&1 &
HEALTH_PID=$!

# Wait a moment for health server to start
sleep 3

# Verify health server is running
if ! kill -0 $HEALTH_PID 2>/dev/null; then
    echo "ERROR: Health server failed to start"
    echo "Check /tmp/celery_worker_health.log for details"
    cat /tmp/celery_worker_health.log 2>/dev/null || true
    exit 1
fi

# Start Celery worker in foreground (Railway monitors this process)
# Use $PYTHON_CMD -m celery to ensure we use the correct Python environment
exec $PYTHON_CMD -m celery -A FutureFish worker -l warning -Q automation,mqtt,analytics --concurrency=4

