# Celery Service Scripts

This directory contains scripts for managing Celery services (worker and beat).

## Start Scripts

- `start_celery_worker.sh` - Start Celery worker with health check server (port 8080)
- `start_celery_beat.sh` - Start Celery beat with health check server (port 8081)

## Kill Scripts

- `kill_celery_worker.sh` - Stop Celery worker and its health server
- `kill_celery_beat.sh` - Stop Celery beat and its health server

## Usage

### Starting Services

```bash
# From project root
./scripts/start_celery_worker.sh
./scripts/start_celery_beat.sh
```

### Stopping Services

```bash
# From project root
./scripts/kill_celery_worker.sh
./scripts/kill_celery_beat.sh
```

## Notes

- Scripts automatically change to the project root directory
- Health servers use different ports (8080 for worker, 8081 for beat) to avoid conflicts
- On Railway, the `PORT` environment variable will override these defaults
