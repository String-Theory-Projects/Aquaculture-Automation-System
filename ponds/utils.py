"""
Utility functions for the ponds app
"""
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_human_readable_error(error, debug_mode=None):
    """
    Convert database and validation errors to human-readable messages
    
    Args:
        error: The error to convert
        debug_mode: If True, includes technical details. If None, uses DEBUG setting
    """
    if debug_mode is None:
        debug_mode = getattr(settings, 'DEBUG', False)
    
    error_str = str(error)
    error_type = type(error).__name__
    
    # Log the original error for debugging
    logger.error(f"Error occurred: {error_type}: {error_str}")
    
    # Database constraint errors
    if "UNIQUE constraint failed" in error_str:
        if "ponds_pond.parent_pair_id, ponds_pond.name" in error_str:
            message = "A pond with this name already exists in this pond pair. Please choose a different name."
        elif "ponds_pondpair.owner, ponds_pondpair.name" in error_str:
            message = "You already have a pond pair with this name. Please choose a different name."
        elif "ponds_pondpair.device_id" in error_str:
            message = "This device is already registered. Each device can only be associated with one pond pair."
        elif "auth_user.username" in error_str:
            message = "This username is already taken. Please choose a different username."
        elif "auth_user.email" in error_str:
            message = "This email address is already registered. Please use a different email or try logging in."
        else:
            message = "This information is already in use. Please choose different values."
        
        if debug_mode:
            return f"{message} (Technical: {error_type}: {error_str})"
        return message
    
    # Foreign key constraint errors
    elif "FOREIGN KEY constraint failed" in error_str:
        message = "Invalid reference detected. Please check your data and try again."
        if debug_mode:
            return f"{message} (Technical: {error_type}: {error_str})"
        return message
    
    # Not null constraint errors
    elif "NOT NULL constraint failed" in error_str:
        if "name" in error_str:
            message = "Pond name is required."
        elif "device_id" in error_str:
            message = "Device ID is required."
        elif "email" in error_str:
            message = "Email address is required."
        elif "username" in error_str:
            message = "Username is required."
        else:
            message = "Required field is missing. Please check your data and try again."
        
        if debug_mode:
            return f"{message} (Technical: {error_type}: {error_str})"
        return message
    
    # Check constraint errors
    elif "CHECK constraint failed" in error_str:
        message = "Invalid data provided. Please check your input values and try again."
        if debug_mode:
            return f"{message} (Technical: {error_type}: {error_str})"
        return message
    
    # Validation errors
    elif isinstance(error, ValidationError):
        if hasattr(error, 'message'):
            message = str(error.message)
        elif hasattr(error, 'messages'):
            message = '; '.join(error.messages)
        else:
            message = str(error)
        
        if debug_mode:
            return f"{message} (Technical: {error_type})"
        return message
    
    # Specific error patterns
    elif "database is locked" in error_str.lower():
        message = "The system is currently busy processing another request. Please wait a moment and try again."
        if debug_mode:
            return f"{message} (Technical: {error_type}: {error_str})"
        return message
    
    elif "no such table" in error_str.lower():
        message = "System error: Required database table not found. Please contact support immediately."
        if debug_mode:
            return f"{message} (Technical: {error_type}: {error_str})"
        return message
    
    elif "permission denied" in error_str.lower():
        message = "You don't have permission to perform this action. Please contact your administrator."
        if debug_mode:
            return f"{message} (Technical: {error_type}: {error_str})"
        return message
    
    elif "connection" in error_str.lower() and "refused" in error_str.lower():
        message = "Unable to connect to the database. Please try again in a moment."
        if debug_mode:
            return f"{message} (Technical: {error_type}: {error_str})"
        return message
    
    elif "timeout" in error_str.lower():
        message = "The request timed out. Please try again with a smaller amount of data or contact support."
        if debug_mode:
            return f"{message} (Technical: {error_type}: {error_str})"
        return message
    
    # HTTP/Network errors
    elif "ConnectionError" in error_type or "connection" in error_str.lower():
        message = "Network connection error. Please check your internet connection and try again."
        if debug_mode:
            return f"{message} (Technical: {error_type}: {error_str})"
        return message
    
    # Memory errors
    elif "MemoryError" in error_type or "memory" in error_str.lower():
        message = "The system is running low on memory. Please try again with less data or contact support."
        if debug_mode:
            return f"{message} (Technical: {error_type}: {error_str})"
        return message
    
    # File system errors
    elif "FileNotFoundError" in error_type or "no such file" in error_str.lower():
        message = "Required file not found. Please contact support."
        if debug_mode:
            return f"{message} (Technical: {error_type}: {error_str})"
        return message
    
    elif "PermissionError" in error_type:
        message = "File permission error. Please contact support."
        if debug_mode:
            return f"{message} (Technical: {error_type}: {error_str})"
        return message
    
    # Default fallback with more specific analysis
    else:
        # Try to extract meaningful parts from the error
        if "constraint" in error_str.lower():
            message = "Data validation failed. Please check your input values and try again."
        elif "duplicate" in error_str.lower():
            message = "This information is already in use. Please choose different values."
        elif "invalid" in error_str.lower():
            message = "Invalid data provided. Please check your input and try again."
        elif "not found" in error_str.lower():
            message = "The requested resource was not found. Please check your input and try again."
        elif "unauthorized" in error_str.lower() or "forbidden" in error_str.lower():
            message = "You don't have permission to perform this action."
        else:
            message = f"An error occurred: {error_str[:100]}{'...' if len(error_str) > 100 else ''}"
        
        if debug_mode:
            return f"{message} (Technical: {error_type}: {error_str})"
        return message


def format_validation_errors(errors, debug_mode=None):
    """
    Format Django REST framework validation errors into human-readable messages
    """
    if isinstance(errors, dict):
        formatted_errors = {}
        for field, field_errors in errors.items():
            if isinstance(field_errors, list):
                formatted_errors[field] = [get_human_readable_error(error, debug_mode) for error in field_errors]
            else:
                formatted_errors[field] = get_human_readable_error(field_errors, debug_mode)
        return formatted_errors
    elif isinstance(errors, list):
        return [get_human_readable_error(error, debug_mode) for error in errors]
    else:
        return get_human_readable_error(errors, debug_mode)


def create_error_response(error, status_code, debug_mode=None):
    """
    Create a standardized error response with optional debug information
    
    Args:
        error: The error to convert
        status_code: HTTP status code
        debug_mode: If True, includes technical details. If None, uses DEBUG setting
    """
    if debug_mode is None:
        debug_mode = getattr(settings, 'DEBUG', False)
    
    error_message = get_human_readable_error(error, debug_mode)
    
    response_data = {
        'error': error_message,
        'status_code': status_code
    }
    
    # Add debug information if in debug mode
    if debug_mode:
        import traceback
        response_data['debug'] = {
            'error_type': type(error).__name__,
            'error_details': str(error),
            'traceback': traceback.format_exc()
        }
    
    return response_data
