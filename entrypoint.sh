#!/bin/bash
set -e

echo "🚀 Starting FutureFish application..."

# Debug database before migrations
echo "🔍 Database Debug Info:"
echo "DB_HOST: ${DB_HOST:-not set}"
echo "DB_NAME: ${DB_NAME:-not set}"  
echo "DB_USER: ${DB_USER:-not set}"
echo "DB_PASSWORD: ${DB_PASSWORD:+set}"

# Wait for database to be ready
echo "⏳ Waiting for database..."
while ! python manage.py check --database default > /dev/null 2>&1; do
    echo "Database is unavailable - sleeping"
    sleep 2
done
echo "✅ Database is ready!"

# Test if we can execute a simple query
echo "🧪 Testing basic database query..."
python -c "
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
        print('✅ Basic query successful')
except Exception as e:
    print(f'❌ Basic query failed: {e}')
    exit(1)
"

# Check if django_migrations table exists
echo "🔍 Checking if django_migrations table exists..."
python -c "
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute(\"SELECT count(*) FROM information_schema.tables WHERE table_name = 'django_migrations'\")
        result = cursor.fetchone()
        if result[0] > 0:
            print('✅ django_migrations table exists')
            cursor.execute('SELECT count(*) FROM django_migrations')
            migration_count = cursor.fetchone()[0]
            print(f'📊 Found {migration_count} existing migrations')
        else:
            print('⚠️ django_migrations table does not exist - this is normal for first deployment')
except Exception as e:
    print(f'❌ Could not check migrations table: {e}')
    exit(1)
"

# Show current migration status
echo "📋 Current migration status:"
python manage.py showmigrations || echo "Could not show migrations (this might be normal for new database)"

# Run database migrations with more verbose output
echo "🗄️ Running database migrations..."
python manage.py migrate --verbosity=2 --noinput || {
    echo "❌ Database migrations failed!"
    echo "🔍 Additional debug info:"
    python manage.py migrate --verbosity=3 --noinput || true
    exit 1
}
echo "✅ Database migrations completed"

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput --clear || {
    echo "❌ Static files collection failed!"
    exit 1
}
echo "✅ Static files collected"

# Create superuser if specified
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "👤 Creating superuser..."
    python manage.py createsuperuser --noinput || echo "ℹ️ Superuser already exists"
fi

echo "🎉 Application startup complete!"
echo "Starting server..."
exec "$@"