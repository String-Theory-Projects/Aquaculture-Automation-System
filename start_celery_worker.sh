#!/bin/bash
# Wrapper script to start Celery worker with health check server
# This allows Railway to monitor the health endpoint while Celery worker runs

set -e

# Function to cleanup on exit
cleanup() {
    if [ ! -z "$HEALTH_PID" ]; then
        kill $HEALTH_PID 2>/dev/null || true
        wait $HEALTH_PID 2>/dev/null || true
    fi
}

trap cleanup EXIT INT TERM

# Start health server in background
python manage.py celery_worker_health > /dev/null 2>&1 &
HEALTH_PID=$!

# Wait a moment for health server to start
sleep 2

# Verify health server is running
if ! kill -0 $HEALTH_PID 2>/dev/null; then
    echo "ERROR: Health server failed to start"
    exit 1
fi

# Start Celery worker in foreground (Railway monitors this process)
exec celery -A FutureFish worker -l warning -Q automation,mqtt,analytics --concurrency=4

