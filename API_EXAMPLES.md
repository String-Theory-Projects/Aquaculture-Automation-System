# API Examples

## Pond Feed Statistics API

### Get Feed Statistics for a Specific Pond

**Endpoint:** `GET /ponds/{pond_id}/feed-stats/`

**Description:** Retrieve feed statistics for a specific pond. Returns statistics grouped by time period (daily, weekly, monthly, yearly).

**Authentication:** Required (Bearer Token)

**Permissions:** User must own the pond (through the pond's parent pair)

**Query Parameters:**
- `stat_type` (optional): Filter by specific stat type ('daily', 'weekly', 'monthly', 'yearly')

**Example Request:**
```bash
curl -X GET \
  "http://localhost:8000/ponds/1/feed-stats/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

**Example Response:**
```json
{
  "pond_id": 1,
  "pond_name": "Main Pond",
  "feed_statistics": {
    "daily": [
      {
        "id": 1,
        "stat_type": "daily",
        "amount": 5.5,
        "start_date": "2024-01-15",
        "updated_at": "2024-01-15T10:30:00Z"
      }
    ],
    "weekly": [
      {
        "id": 2,
        "stat_type": "weekly",
        "amount": 25.0,
        "start_date": "2024-01-15",
        "updated_at": "2024-01-15T10:30:00Z"
      }
    ],
    "monthly": [
      {
        "id": 3,
        "stat_type": "monthly",
        "amount": 100.0,
        "start_date": "2024-01-01",
        "updated_at": "2024-01-15T10:30:00Z"
      }
    ]
  },
  "total_records": 3
}
```

**Filter by Stat Type:**
```bash
curl -X GET \
  "http://localhost:8000/ponds/1/feed-stats/?stat_type=daily" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

**Response for filtered request:**
```json
{
  "pond_id": 1,
  "pond_name": "Main Pond",
  "feed_statistics": {
    "daily": [
      {
        "id": 1,
        "stat_type": "daily",
        "amount": 5.5,
        "start_date": "2024-01-15",
        "updated_at": "2024-01-15T10:30:00Z"
      }
    ]
  },
  "total_records": 1
}
```

**Error Responses:**

**401 Unauthorized (No Authentication):**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden (Wrong Owner):**
```json
{
  "error": "You don't have permission to access this pond's feed statistics"
}
```

**404 Not Found (Pond Doesn't Exist):**
```json
{
  "detail": "Not found."
}
```

**400 Bad Request (Invalid Stat Type):**
```json
{
  "error": "Invalid stat_type. Must be one of: daily, weekly, monthly, yearly"
}
```

## Feed Event Logging API

### Log Feed Event

**Endpoint:** `POST /automation/feed/log-event/`

**Description:** Log a feed event from Lambda or external systems. Creates a feed event record and updates feed statistics.

**Authentication:** Not required (for Lambda integration)

**Request Body:**
```json
{
  "user_id": 123,
  "pond_id": 321,
  "amount": 7.5
}
```

**Example Request:**
```bash
curl -X POST \
  "http://localhost:8000/automation/feed/log-event/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "pond_id": 321,
    "amount": 7.5
  }'
```

**Example Response:**
```json
{
  "status": "logged"
}
```

**Error Responses:**

**400 Bad Request (Invalid Data):**
```json
{
  "error": "Invalid data"
}
```

### Notes

- The Feed Statistics API automatically groups statistics by `stat_type` for better organization
- Statistics are ordered by `start_date` (newest first)
- The `amount` field represents feed amount in kilograms
- Only authenticated users who own the pond can access feed statistics
- The pond ownership is determined through the pond's parent pair relationship
- Feed events are automatically logged and statistics are updated in real-time
- The Feed Event Logging API is designed for Lambda integration and doesn't require authentication