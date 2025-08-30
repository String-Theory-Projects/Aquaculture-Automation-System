# PondPair API Documentation

## Overview
The PondPair API manages pairs of ponds controlled by ESP32 devices. Each PondPair represents a physical ESP32 device that can control up to 2 ponds.

## Device ID Format
All `device_id` fields must be valid MAC addresses in the format `XX:XX:XX:XX:XX:XX` where X represents hexadecimal digits (0-9, A-F).

**Examples:**
- `AA:BB:CC:DD:EE:FF`
- `12:34:56:78:9A:BC`
- `FE:DC:BA:98:76:54`

## Authentication
All endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Base URL

```
http://localhost:8000/
```

---

## Endpoints

### 1. List and Create Pond Pairs

**Endpoint:** `GET/POST /pond-pairs/`

#### GET - List Pond Pairs
Returns all pond pairs for the authenticated user.

**Response:**
```json
[
    {
        "id": 1,
        "device_id": "DD:EE:FF:AA:BB:CC",
        "owner": 1,
        "owner_username": "john_doe",
        "created_at": "2024-01-15T10:30:00Z",
        "ponds": [
            {
                "id": 1,
                "name": "Main Pond",
                "is_active": true,
                "created_at": "2024-01-15T10:30:00Z"
            },
            {
                "id": 2,
                "name": "Nursery Pond",
                "is_active": true,
                "created_at": "2024-01-15T10:30:00Z"
            }
        ],
        "pond_count": 2,
        "is_complete": true
    }
]
```

#### POST - Create Pond Pair
Creates a new pond pair with initial ponds.

**Request Body:**
```json
{
    "device_id": "BB:CC:DD:EE:FF:AA",
    "pond_names": ["Main Pond", "Nursery Pond"]
}
```

**Response:** Same as GET response for the created pair.

**Validation Rules:**
- `device_id`: Must be a valid MAC address in format XX:XX:XX:XX:XX:XX, unique
- `pond_names`: Array of 1-2 pond names (strings, max 100 characters each)

---

### 2. Get Pond Pair Details

**Endpoint:** `GET /pond-pairs/{id}/`

Returns detailed information about a specific pond pair.

**Response:**
```json
{
  "id": 1,
  "device_id": "ESP32_001",
  "owner": 1,
  "owner_username": "user1",
  "created_at": "2024-01-15T10:30:00Z",
  "ponds": [
    {
      "id": 1,
      "name": "Main Pond",
      "parent_pair": 1,
      "parent_pair_device_id": "ESP32_001",
      "owner_username": "user1",
      "created_at": "2024-01-15T10:30:00Z",
      "is_active": true
    }
  ],
  "pond_count": 1,
  "is_complete": false
}
```

---

### 3. Update Pond Pair

**Endpoint:** `PUT/PATCH /pond-pairs/{id}/`

Updates pond pair information.

**Request Body:**
```json
{
  "device_id": "ESP32_001_UPDATED"
}
```

**Response:** Same as GET response with updated data.

---

### 4. Delete Pond Pair

**Endpoint:** `DELETE /pond-pairs/{id}/`

Deletes a pond pair and all its associated ponds.

**Response:**
```json
{
  "message": "Pond pair and 2 ponds deleted successfully"
}
```

---

### 5. Get Pond Pair with Full Details

**Endpoint:** `GET /pond-pairs/{id}/details/`

Returns comprehensive information including controls and sensor data.

**Response:**
```json
{
  "id": 1,
  "device_id": "ESP32_001",
  "owner": 1,
  "owner_username": "user1",
  "created_at": "2024-01-15T10:30:00Z",
  "ponds": [
    {
      "id": 1,
      "name": "Main Pond",
      "parent_pair": 1,
      "parent_pair_device_id": "ESP32_001",
      "owner_username": "user1",
      "created_at": "2024-01-15T10:30:00Z",
      "is_active": true,
      "control": {
        "water_valve_state": true,
        "last_feed_time": "2024-01-15T10:30:00Z",
        "last_feed_amount": 5.0
      },
      "recent_sensor_data": {
        "temperature": 25.5,
        "water_level": 80.0,
        "feed_level": 75.0,
        "turbidity": 10.0,
        "dissolved_oxygen": 8.5,
        "ph": 7.2,
        "timestamp": "2024-01-15T10:30:00Z"
      }
    }
  ],
  "pond_count": 1,
  "is_complete": false,
  "total_feed_amount": 10.5
}
```

---

### 6. Get Pond Pair Summary List

**Endpoint:** `GET /pond-pairs/summary/`

Returns a lightweight summary of all pond pairs.

**Response:**
```json
[
  {
    "id": 1,
    "device_id": "ESP32_001",
    "pond_count": 2,
    "is_complete": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### 7. Get Pond Pair by Device ID

**Endpoint:** `GET /pond-pairs/device/{device_id}/`

Returns pond pair information by device ID.

**Response:** Same as GET /pond-pairs/{id}/

---

### 8. Add Pond to Pair

**Endpoint:** `POST /pond-pairs/{pond_pair_id}/add-pond/`

Adds a new pond to an existing pond pair.

**Request Body:**
```json
{
  "name": "Additional Pond"
}
```

**Response:** Same as GET /pond-pairs/{id}/ with updated pond list.

**Validation Rules:**
- Pond pair must have fewer than 2 ponds
- Pond name must be unique for the user
- Pond name is required

---

### 9. Remove Pond from Pair

**Endpoint:** `DELETE /pond-pairs/{pond_pair_id}/remove-pond/{pond_id}/`

Removes a pond from an existing pond pair.

**Response:** Same as GET /pond-pairs/{id}/ with updated pond list.

**Validation Rules:**
- Cannot remove the last pond from a pair (minimum 1 pond required)
- User must own the pond
- Pond must belong to the specified pair

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "A PondPair can have at most 2 ponds"
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "error": "You don't have permission to access this pond pair"
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 500 Internal Server Error
```json
{
  "error": "An error occurred while processing your request"
}
```

---

## Usage Examples

### Create a New Pond Pair
```bash
curl -X POST \
  "http://localhost:8000/pond-pairs/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_001",
    "pond_names": ["Main Pond", "Secondary Pond"]
  }'
```

### List All Pond Pairs
```bash
curl -X GET \
  "http://localhost:8000/pond-pairs/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get Detailed Information
```bash
curl -X GET \
  "http://localhost:8000/pond-pairs/1/details/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Add Pond to Existing Pair
```bash
curl -X POST \
  "http://localhost:8000/pond-pairs/1/add-pond/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Third Pond"
  }'
```

### Remove Pond from Pair
```bash
curl -X DELETE \
  "http://localhost:8000/pond-pairs/1/remove-pond/2/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update Device ID
```bash
curl -X PATCH \
  "http://localhost:8000/pond-pairs/1/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ESP32_001_UPDATED"
  }'
```

---

## Data Model

### PondPair Properties
- `id`: Unique identifier
- `device_id`: ESP32 device identifier (unique)
- `owner`: User who owns the pair
- `created_at`: Creation timestamp
- `pond_count`: Number of ponds in the pair (1-2)
- `is_complete`: Whether the pair has exactly 2 ponds

### Pond Properties
- `id`: Unique identifier
- `name`: Pond name
- `parent_pair`: Associated PondPair
- `is_active`: Whether the pond is active
- `created_at`: Creation timestamp

---

## Notes

1. **Ownership**: Users can only access pond pairs they own
2. **Validation**: Pond pairs must have 1-2 ponds (minimum 1, maximum 2)
3. **Cascading**: Deleting a pond pair deletes all associated ponds
4. **Device ID**: Must be unique across all pond pairs
5. **Pond Names**: Must be unique per user across all their ponds
6. **Minimum Requirement**: A PondPair cannot exist without at least one pond 