# MQTT Testing Guide

## Overview
This guide provides comprehensive testing commands for the Future Fish Dashboard MQTT system. The application uses device-level topics with the EMQX broker.

## MQTT Configuration
- **Broker**: `broker.emqx.io:1883`
- **Username**: `futurefish_backend`
- **Password**: `7-33@98:epY}`
- **Client ID**: `futurefish_backend_{random_hex}`

## Topic Structure
The application uses device-level topics (NOT pond-level topics):

```
devices/{device_id}/data/heartbeat      # Device heartbeat (10s intervals)
devices/{device_id}/data/startup       # Device startup + firmware info
devices/{device_id}/data/sensors       # Sensor data from devices
devices/{device_id}/commands           # Commands sent TO devices
devices/{device_id}/ack                # Command acknowledgments
devices/{device_id}/threshold          # Threshold updates
```

## Testing Commands

### 1. Subscribe to Device Data
```bash
# Subscribe to all device data
mosquitto_sub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" -t "devices/+/data/+" -v

# Subscribe to specific device sensors
mosquitto_sub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" -t "devices/DEVICE_ID/data/sensors" -v

# Subscribe to device heartbeats
mosquitto_sub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" -t "devices/+/data/heartbeat" -v
```

### 2. Subscribe to Commands
```bash
# Subscribe to all device commands
mosquitto_sub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" -t "devices/+/commands" -v

# Subscribe to specific device commands
mosquitto_sub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" -t "devices/DEVICE_ID/commands" -v
```

### 3. Subscribe to Acknowledgments
```bash
# Subscribe to all device acknowledgments
mosquitto_sub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" -t "devices/+/ack" -v

# Subscribe to specific device acknowledgments
mosquitto_sub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" -t "devices/DEVICE_ID/ack" -v
```

### 4. Test Feed Commands
```bash
# Send a feed command (replace DEVICE_ID with actual device ID)
mosquitto_pub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" \
  -t "devices/DEVICE_ID/commands" \
  -m '{
    "command_id": "test_feed_123",
    "command_type": "FEED",
    "pond_position": 1,
    "parameters": {"amount": 150},
    "timestamp": "2025-08-29T21:00:00Z"
  }' \
  -q 2

# Send a water command
mosquitto_pub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" \
  -t "devices/DEVICE_ID/commands" \
  -m '{
    "command_id": "test_water_123",
    "command_type": "WATER_FILL",
    "pond_position": 1,
    "parameters": {"target_water_level": 80},
    "timestamp": "2025-08-29T21:00:00Z"
  }' \
  -q 2
```

### 5. Test Device Responses
```bash
# Simulate device acknowledgment (replace DEVICE_ID and COMMAND_ID)
mosquitto_pub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" \
  -t "devices/DEVICE_ID/ack" \
  -m '{
    "command_id": "COMMAND_ID",
    "success": true,
    "message": "Feed command executed successfully",
    "timestamp": "2025-08-29T21:00:00Z"
  }' \
  -q 1

# Simulate sensor data
mosquitto_pub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" \
  -t "devices/DEVICE_ID/data/sensors" \
  -m '{
    "temperature": 25.5,
    "water_level": 75.2,
    "feed_level": 45.8,
    "turbidity": 12.3,
    "dissolved_oxygen": 8.1,
    "ph": 7.2,
    "ammonia": 0.05,
    "battery": 87.3,
    "signal_strength": -45,
    "timestamp": "2025-08-29T21:00:00Z"
  }' \
  -q 1
```

## Testing Workflow

### 1. Start Monitoring
```bash
# Terminal 1: Monitor all device data
mosquitto_sub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" -t "devices/+/data/+" -v

# Terminal 2: Monitor commands
mosquitto_sub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" -t "devices/+/commands" -v

# Terminal 3: Monitor acknowledgments
mosquitto_sub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" -t "devices/+/ack" -v
```

### 2. Send Test Commands
```bash
# Send feed command
mosquitto_pub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" \
  -t "devices/DEVICE_ID/commands" \
  -m '{"command_id": "test_001", "command_type": "FEED", "pond_position": 1, "parameters": {"amount": 100}}' \
  -q 2
```

### 3. Verify Application Response
- Check Django logs for command processing
- Verify database records in `DeviceCommand` table
- Check automation execution records

## Troubleshooting

### Common Issues
1. **Connection Failed**: Verify broker host and credentials
2. **No Messages**: Check topic structure and wildcards
3. **Authentication Error**: Verify username/password
4. **QoS Issues**: Use QoS 2 for commands, QoS 1 for data

### Debug Commands
```bash
# Test connection without authentication
mosquitto_sub -h "broker.emqx.io" -t "test/topic" -v

# Test with verbose output
mosquitto_sub -h "broker.emqx.io" -u "futurefish_backend" -P "7-33@98:epY}" -t "devices/+/data/+" -v -d
```

## Integration Testing

### 1. Test Complete Feed Workflow
1. Send feed command via API endpoint `/automation/ponds/{id}/control/feed/` (DRF APIView)
2. Verify command appears in Django admin
3. Simulate device acknowledgment
4. Verify automation execution completion

### 2. Test Complete Water Control Workflow
1. Send water command via API endpoint `/automation/ponds/{id}/control/water/` (DRF APIView)
2. Verify command appears in Django admin
3. Simulate device acknowledgment
4. Verify automation execution completion

### 2. Test Sensor Data Processing
1. Send sensor data via MQTT
2. Verify data appears in Django admin
3. Check threshold violations
4. Verify automation triggers

### 3. Test Error Handling
1. Send malformed commands
2. Test timeout scenarios
3. Verify retry logic
4. Check error logging

## Notes
- Replace `DEVICE_ID` with actual device IDs from your system
- Use QoS 2 for commands (exactly once delivery)
- Use QoS 1 for data (at least once delivery)
- Monitor Django logs for application-side processing
- Check database tables for data persistence
