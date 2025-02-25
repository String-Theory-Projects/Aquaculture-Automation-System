# mqtt/constants.py
import os

# Base topic structure
BASE_TOPIC = os.getenv('MQTT_BASE_TOPIC', "futurefish/ponds/{pond_id}")

# BROKER INFO
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', "")
MQTT_USERNAME = os.getenv('MQTT_USERNAME', "futurefish_backend")
MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', "broker.emqx.io")
MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', "8883"))

# Control topics (QoS 2)
CONTROL_FEED_TOPIC = os.getenv('MQTT_CONTROL_FEED_TOPIC', f"{BASE_TOPIC}/control/feed")
CONTROL_WATER_TOPIC = os.getenv('MQTT_CONTROL_WATER_TOPIC', f"{BASE_TOPIC}/control/water")
AUTOMATION_FEED_TOPIC = os.getenv('MQTT_AUTOMATION_FEED_TOPIC', f"{BASE_TOPIC}/automation/feed")
AUTOMATION_WATER_TOPIC = os.getenv('MQTT_AUTOMATION_WATER_TOPIC', f"{BASE_TOPIC}/automation/water")

# Status topics (QoS 1)
STATUS_FEED_TOPIC = os.getenv('MQTT_STATUS_FEED_TOPIC', f"{BASE_TOPIC}/status/feed")
STATUS_WATER_TOPIC = os.getenv('MQTT_STATUS_WATER_TOPIC', f"{BASE_TOPIC}/status/water")
STATUS_AUTOMATION_TOPIC = os.getenv('MQTT_STATUS_AUTOMATION_TOPIC', f"{BASE_TOPIC}/status/automation")

# QoS Levels
CONTROL_QOS = int(os.getenv('MQTT_CONTROL_QOS', "2"))
STATUS_QOS = int(os.getenv('MQTT_STATUS_QOS', "1"))

# Message Types
COMMAND_TYPE = os.getenv('MQTT_COMMAND_TYPE', 'COMMAND')
STATUS_TYPE = os.getenv('MQTT_STATUS_TYPE', 'STATUS')

# Message Status
MESSAGE_SENT = os.getenv('MQTT_MESSAGE_SENT', 'SENT')
MESSAGE_RECEIVED = os.getenv('MQTT_MESSAGE_RECEIVED', 'RECEIVED')
MESSAGE_ERROR = os.getenv('MQTT_MESSAGE_ERROR', 'ERROR')
MESSAGE_TIMEOUT = os.getenv('MQTT_MESSAGE_TIMEOUT', 'TIMEOUT')

# Control Actions
ACTION_FEED = os.getenv('MQTT_ACTION_FEED', 'feed')
ACTION_WATER = os.getenv('MQTT_ACTION_WATER', 'water')

# Command Types
COMMAND_MANUAL = os.getenv('MQTT_COMMAND_MANUAL', 'manual')
COMMAND_AUTOMATION = os.getenv('MQTT_COMMAND_AUTOMATION', 'automation')
