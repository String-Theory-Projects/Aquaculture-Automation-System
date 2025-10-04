# Improved Error Handling Examples

## Before vs After

### 1. Database Constraint Error

**Before:**
```json
{
    "error": "UNIQUE constraint failed: ponds_pond.parent_pair_id, ponds_pond.name"
}
```

**After (Production Mode):**
```json
{
    "error": "A pond with this name already exists in this pond pair. Please choose a different name.",
    "status_code": 400
}
```

**After (Debug Mode):**
```json
{
    "error": "A pond with this name already exists in this pond pair. Please choose a different name. (Technical: IntegrityError: UNIQUE constraint failed: ponds_pond.parent_pair_id, ponds_pond.name)",
    "status_code": 400,
    "debug": {
        "error_type": "IntegrityError",
        "error_details": "UNIQUE constraint failed: ponds_pond.parent_pair_id, ponds_pond.name",
        "traceback": null
    }
}
```

### 2. Generic Error

**Before:**
```json
{
    "error": "An unexpected error occurred. Please try again or contact support if the problem persists."
}
```

**After (Production Mode):**
```json
{
    "error": "An error occurred: Something went wrong with the database connection",
    "status_code": 500
}
```

**After (Debug Mode):**
```json
{
    "error": "An error occurred: Something went wrong with the database connection (Technical: Exception: Something went wrong with the database connection)",
    "status_code": 500,
    "debug": {
        "error_type": "Exception",
        "error_details": "Something went wrong with the database connection",
        "traceback": null
    }
}
```

### 3. Network Error

**Before:**
```json
{
    "error": "An unexpected error occurred. Please try again or contact support if the problem persists."
}
```

**After (Production Mode):**
```json
{
    "error": "Network connection error. Please check your internet connection and try again.",
    "status_code": 500
}
```

**After (Debug Mode):**
```json
{
    "error": "Network connection error. Please check your internet connection and try again. (Technical: ConnectionError: Failed to connect to database)",
    "status_code": 500,
    "debug": {
        "error_type": "ConnectionError",
        "error_details": "Failed to connect to database",
        "traceback": null
    }
}
```

## Key Improvements

1. **Specific Error Messages**: Each error type now has a specific, actionable message
2. **Debug Mode Support**: Developers can see technical details when needed
3. **Better Error Classification**: Errors are categorized by type and context
4. **User-Friendly Language**: Technical jargon is replaced with clear instructions
5. **Consistent Format**: All errors follow the same response structure

## Debug Mode Detection

The system automatically detects debug mode based on Django's `DEBUG` setting:
- **Production** (`DEBUG=False`): Shows only user-friendly messages
- **Development** (`DEBUG=True`): Shows both user-friendly and technical details

## Error Types Covered

- Database constraint errors (UNIQUE, FOREIGN KEY, NOT NULL, CHECK)
- Validation errors
- Network/Connection errors
- Memory errors
- File system errors
- Permission errors
- Timeout errors
- Generic errors with context extraction
