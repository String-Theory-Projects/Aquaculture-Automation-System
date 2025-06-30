#!/bin/bash
set -e

echo "Starting FutureFish application..."

# Wait for database to be ready
echo "Waiting for database..."
while ! python manage.py check --database default > /dev/null 2>&1; do
    echo "Database is unavailable - sleeping"
    sleep 2
done
echo "Database is ready!"

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Starting server..."
exec "$@"