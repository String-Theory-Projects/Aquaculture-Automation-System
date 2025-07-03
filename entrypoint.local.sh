#!/usr/bin/env bash

# Optional: Load .env.local manually if needed
if [ -f ".env.local" ]; then
  export $(cat .env.local | grep -v '^#' | xargs)
fi

python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput
python3 -m gunicorn --bind 0.0.0.0:8000 --workers 3 FutureFish.wsgi:application
