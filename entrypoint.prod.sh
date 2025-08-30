#!/usr/bin/env bash

export DJANGO_SETTINGS_MODULE=FutureFish.settings.prod

echo "Collecting static files..."
python3 manage.py collectstatic --noinput

echo "Running migrations..."
python3 manage.py migrate --noinput || { echo "Migration failed"; exit 1; }

echo "Starting Gunicorn..."
python3 -m gunicorn --bind 0.0.0.0:8000 --workers 3 FutureFish.wsgi:application
