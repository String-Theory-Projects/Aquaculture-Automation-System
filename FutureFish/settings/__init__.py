# Settings package for FutureFish
# Import the appropriate settings based on environment
import os

# Default to development settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FutureFish.settings.dev')
