"""
Core constants for the Future Fish Dashboard project.
Centralized configuration for all apps.
"""

# Device ID settings
DEVICE_ID_MIN_LENGTH = 17  # MAC address format: XX:XX:XX:XX:XX:XX

# System user settings
SYSTEM_USERNAME = 'system'
SYSTEM_EMAIL = 'system@futurefishagro.com'

# MQTT Topics
MQTT_TOPICS = {
    'HEARTBEAT': 'devices/{device_id}/data/heartbeat',
    'STARTUP': 'devices/{device_id}/data/startup',
    'SENSORS': 'devices/{device_id}/data/sensors',
    'COMMANDS': 'devices/{device_id}/commands',
    'ACK': 'devices/{device_id}/ack',
    'THRESHOLD': 'devices/{device_id}/threshold',
}

# MQTT Settings
MQTT_BROKER_HOST = 'broker.emqx.io'
MQTT_BROKER_PORT = 1883
MQTT_KEEPALIVE = 60
MQTT_TIMEOUT = 10
MQTT_USERNAME = 'futurefish_backend'
MQTT_PASSWORD = '7-33@98:epY}'

# WebSocket Settings
WEBSOCKET_UPDATE_INTERVAL = 5  # seconds
MAX_CONCURRENT_CONNECTIONS_PER_USER = 10

# Automation Settings
AUTOMATION_PRIORITIES = [
    'MANUAL_COMMAND',      # Highest priority
    'EMERGENCY_WATER',     # Critical thresholds
    'SCHEDULED',           # User schedules
    'THRESHOLD',           # Sensor triggers
]

# Threshold Settings
DEFAULT_THRESHOLD_TIMEOUT = 30  # seconds
MAX_THRESHOLD_VIOLATIONS = 3    # before triggering action

# Feed Settings
DEFAULT_FEED_AMOUNT = 100  # grams
MAX_FEED_AMOUNT = 1000     # grams
MIN_FEED_AMOUNT = 10       # grams

# Water Settings
DEFAULT_WATER_LEVEL = 80   # percentage
MIN_WATER_LEVEL = 20       # percentage
MAX_WATER_LEVEL = 100      # percentage

# Sensor Validation Ranges
SENSOR_RANGES = {
    'temperature': {'min': 0, 'max': 50},
    'water_level': {'min': 0, 'max': 100},
    'feed_level': {'min': 0, 'max': 100},
    'turbidity': {'min': 0, 'max': 1000},
    'dissolved_oxygen': {'min': 0, 'max': 20},
    'ph': {'min': 0, 'max': 14},
    'ammonia': {'min': 0, 'max': 100},
    'battery': {'min': 0, 'max': 100},
}

# Pagination Settings
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

# Cache Settings
CACHE_TIMEOUT = 300  # 5 minutes
CACHE_KEY_PREFIX = 'futurefish'

# API Settings
API_VERSION = 'v1'
API_RATE_LIMIT = '100/hour'

# Logging Settings
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# Security Settings
JWT_ACCESS_TOKEN_LIFETIME_DAYS = 60
JWT_REFRESH_TOKEN_LIFETIME_DAYS = 14
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

# Database Settings
DB_CONNECTION_TIMEOUT = 30
DB_QUERY_TIMEOUT = 60

# Celery Settings
CELERY_TASK_TIMEOUT = 300  # 5 minutes
CELERY_MAX_RETRIES = 3
CELERY_RETRY_DELAY = 60    # 1 minute
