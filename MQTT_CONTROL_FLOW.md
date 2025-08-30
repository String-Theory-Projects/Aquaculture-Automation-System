# MQTT Control Flow: Button Click to Command History

## 🔄 Complete Flow Overview

```
User Button Click → API → Service → MQTT Client → Device → Acknowledgment → History Logs
```

---

## 1. 🖱️ User Button Click (Frontend)

**Location:** React frontend component (e.g., `FeedControl.jsx`)
**Action:** User clicks "Feed" button with amount parameter
**Data:** `{ amount: 100 }` (grams)

---

## 2. 🌐 API Request (Django REST Framework)

**Endpoint:** `POST /automation/ponds/{pond_id}/control/feed/`
**View:** `ExecuteFeedCommandView.post()`
**Authentication:** JWT Bearer token required

### Branch Points:
- ✅ **Success:** User authenticated, pond ownership verified
- ❌ **Error 401:** Invalid/missing JWT token
- ❌ **Error 403:** User doesn't own the pond
- ❌ **Error 400:** Invalid amount parameter (≤0)
- ❌ **Error 500:** Server/database error

### Function Calls:
```python
# 1. Authentication check
permission_classes = [IsAuthenticated]

# 2. Pond ownership verification
if pond.parent_pair.owner != request.user:
    return Response({'error': 'Access denied'}, status=403)

# 3. Parameter validation
amount = float(data.get('amount', 100))
if amount <= 0:
    return Response({'error': 'Amount must be positive'}, status=400)

# 4. Service call
service = AutomationService()
execution = service.execute_manual_automation(
    pond=pond,
    action='FEED',
    parameters={'feed_amount': amount},
    user=request.user
)
```

---

## 3. 🏭 Service Layer (AutomationService)

**Method:** `execute_manual_automation()`
**Purpose:** Creates automation execution record and triggers MQTT command

### Branch Points:
- ✅ **Success:** Automation created, MQTT command sent
- ❌ **Error:** Database transaction failed
- ❌ **Error:** Invalid action type

### Function Calls:
```python
# 1. Create automation execution
automation = AutomationExecution.objects.create(
    pond=pond,
    execution_type='FEED',
    action='FEED',
    priority='MANUAL_COMMAND',
    status='EXECUTING',
    user=user,
    parameters=parameters
)

# 2. Send MQTT command
command_id = self.mqtt_service.send_feed_command(
    pond_pair=pond.parent_pair,
    amount=feed_amount,
    pond=pond,
    user=user
)
```

---

## 4. 📡 MQTT Service Layer (MQTTService)

**Method:** `send_feed_command()`
**Purpose:** Prepares command parameters and calls MQTT client

### Branch Points:
- ✅ **Success:** Command parameters prepared, MQTT client called
- ❌ **Error:** Invalid pond pair or pond data
- ❌ **Error:** MQTT client not available

### Function Calls:
```python
# 1. Prepare command parameters
parameters = {
    'action': 'feed',
    'amount': amount,
    'timestamp': timezone.now().isoformat()
}

# 2. Send via MQTT client
command_id = self.client.send_command(
    pond_pair=pond_pair,
    command_type='FEED',
    parameters=parameters,
    pond=pond
)
```

---

## 5. 🔌 MQTT Client (MQTTClient)

**Method:** `send_command()`
**Purpose:** Publishes command to MQTT broker and tracks acknowledgment

### Branch Points:
- ✅ **Success:** Command published, tracking started
- ❌ **Error:** MQTT client not connected
- ❌ **Error:** No ponds found for pond pair
- ❌ **Error:** MQTT publish failed

### Function Calls:
```python
# 1. Connection check
if not self.is_connected:
    logger.error("MQTT client not connected")
    return None

# 2. Create device command record
command = DeviceCommand.objects.create(
    pond=pond,
    command_type=command_type,
    status='PENDING',
    parameters=parameters,
    timeout_seconds=10,
    max_retries=3
)

# 3. Prepare MQTT message
message = {
    'command_id': str(command.command_id),
    'command_type': command_type,
    'pond_position': pond.position,
    'parameters': parameters,
    'timestamp': timezone.now().isoformat()
}

# 4. Publish to MQTT broker
topic = f"devices/{pond_pair.device_id}/commands"
result, mid = self.client.publish(
    topic,
    json.dumps(message),
    qos=2,  # Exactly once delivery
    retain=False
)

# 5. Track pending command
self.pending_commands[str(command.command_id)] = command
self.command_timeouts[str(command.command_id)] = time.time() + command.timeout_seconds
```

---

## 6. 📨 MQTT Message Structure

**Topic:** `devices/{device_id}/commands`
**Payload:**
```json
{
    "command_id": "uuid-string",
    "command_type": "FEED",
    "pond_position": 1,
    "parameters": {
        "action": "feed",
        "amount": 100,
        "timestamp": "2025-08-30T01:00:00Z"
    },
    "timestamp": "2025-08-30T01:00:00Z"
}
```

---

## 7. 📱 Device Processing (ESP32)

**Device receives MQTT message and:**
1. **Validates command** format and parameters
2. **Executes action** (feed motor control, water valve control)
3. **Sends acknowledgment** back to MQTT broker

---

## 8. 📬 Acknowledgment Processing

**Topic:** `devices/{device_id}/ack`
**Payload:**
```json
{
    "command_id": "uuid-string",
    "success": true,
    "message": "Feed command executed successfully",
    "timestamp": "2025-08-30T01:00:01Z"
}
```

### Branch Points:
- ✅ **Success:** Command completed successfully
- ❌ **Error:** Command failed (hardware error, invalid parameters)
- ❌ **Timeout:** No acknowledgment received within 10 seconds

---

## 9. 🔄 Command Status Updates

**DeviceCommand model status flow:**
```
PENDING → SENT → ACKNOWLEDGED → COMPLETED
   ↓         ↓         ↓            ↓
 Created  Published  Device      Success/
          to MQTT   Received     Failed
```

**AutomationExecution model status flow:**
```
EXECUTING → COMPLETED/FAILED
    ↓            ↓
  Started    Based on ACK
```

---

## 10. 📊 Command History Logs

**Database Records Created:**

1. **AutomationExecution** - High-level execution record
2. **DeviceCommand** - Low-level MQTT command tracking  
3. **MQTTMessage** - MQTT publish/subscribe logs
4. **Logs** - Django application logs

### Log Entries:
```
INFO - Created manual automation 4 for Pond 1: FEED
INFO - Command uuid-123 sent to device AA:BB:CC:DD:EE:FF for pond 1
INFO - Command uuid-123 acknowledged successfully
INFO - Automation 4 completed successfully via command uuid-123
```

---

## 🔀 Error Handling & Retry Logic

### Timeout Handling:
- **Command timeout:** 10 seconds
- **Max retries:** 3 attempts
- **Retry strategy:** Exponential backoff

### Connection Handling:
- **Auto-reconnection** if MQTT client disconnects
- **Connection monitoring** every 10 seconds
- **Graceful degradation** if broker unavailable

---

## 📈 Success Response Flow

```json
{
    "success": true,
    "data": {
        "execution_id": 4,
        "message": "Feed command executed successfully for Test Pond",
        "feed_amount": 100
    }
}
```

## ❌ Error Response Examples

### Authentication Error (401):
```json
{
    "detail": "Authentication credentials were not provided."
}
```

### Access Denied (403):
```json
{
    "success": false,
    "error": "Access denied"
}
```

### MQTT Connection Error (500):
```json
{
    "success": false,
    "error": "MQTT client not connected"
}
```

---

## 🎯 Key Components Summary

1. **ExecuteFeedCommandView** - DRF APIView with JWT authentication
2. **AutomationService** - Business logic layer
3. **MQTTService** - MQTT command preparation
4. **MQTTClient** - MQTT broker communication
5. **DeviceCommand** - Command tracking model
6. **AutomationExecution** - High-level execution tracking

---

## 🔧 MQTT Topics Used

| Topic | Purpose | Direction |
|-------|---------|-----------|
| `devices/{device_id}/commands` | Send commands to device | Publish |
| `devices/{device_id}/ack` | Receive command acknowledgments | Subscribe |
| `devices/{device_id}/data/sensors` | Receive sensor data | Subscribe |
| `devices/{device_id}/data/heartbeat` | Device health monitoring | Subscribe |
| `devices/{device_id}/data/startup` | Device startup notifications | Subscribe |
| `devices/{device_id}/threshold` | Threshold violation alerts | Subscribe |

---

## 📋 Database Models Involved

### AutomationExecution
- **Purpose:** High-level automation tracking
- **Key Fields:** pond, execution_type, action, priority, status, user, parameters
- **Status Flow:** PENDING → EXECUTING → COMPLETED/FAILED

### DeviceCommand
- **Purpose:** Low-level MQTT command tracking
- **Key Fields:** command_id, pond, command_type, status, parameters, timeout_seconds
- **Status Flow:** PENDING → SENT → ACKNOWLEDGED → COMPLETED

### MQTTMessage
- **Purpose:** MQTT communication logging
- **Key Fields:** pond_pair, topic, message_type, payload, success, correlation_id

---

## 🚀 Performance Considerations

### Response Times:
- **API Response:** < 100ms (database operations)
- **MQTT Publish:** < 50ms (local network)
- **Device Processing:** 1-5 seconds (hardware dependent)
- **Total Round Trip:** 2-6 seconds

### Scalability:
- **Concurrent Commands:** Limited by MQTT broker capacity
- **Command Queue:** In-memory tracking with database persistence
- **Error Recovery:** Automatic retry with exponential backoff

---

## 🔍 Debugging & Monitoring

### Log Levels:
- **INFO:** Normal operation flow
- **WARNING:** Non-critical issues
- **ERROR:** Command failures, connection issues
- **DEBUG:** Detailed MQTT message content

### Monitoring Points:
1. **MQTT Connection Status** - Client connectivity
2. **Command Success Rate** - Acknowledgment ratio
3. **Response Times** - End-to-end latency
4. **Error Patterns** - Common failure modes

---

## 📚 Related Documentation

- [API Endpoints](./README.md#api-endpoints)
- [MQTT Testing Guide](./MQTT_TESTING_GUIDE.md)
- [Automation Models](./automation/models.py)
- [MQTT Client Implementation](./mqtt_client/client.py)

---

*This document provides a comprehensive overview of the MQTT control flow implementation in the Future Fish Dashboard system.*
