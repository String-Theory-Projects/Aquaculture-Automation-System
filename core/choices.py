"""
Core choices for the Future Fish Dashboard project.
Centralized model choices for all apps.
"""

# Automation Types
AUTOMATION_TYPES = [
    ('FEED', 'Feeding'),
    ('WATER', 'Water Change'),
]

# Feed Stat Types
FEED_STAT_TYPES = [
    ('daily', 'Daily'),
    ('weekly', 'Weekly'),
    ('monthly', 'Monthly'),
    ('yearly', 'Yearly')
]

# Alert Levels
ALERT_LEVELS = [
    ('LOW', 'Low'),
    ('MEDIUM', 'Medium'),
    ('HIGH', 'High'),
    ('CRITICAL', 'Critical'),
]

# Alert Status
ALERT_STATUS = [
    ('active', 'Active'),
    ('acknowledged', 'Acknowledged'),
    ('resolved', 'Resolved'),
    ('dismissed', 'Dismissed'),
]

# Device Log Types
LOG_TYPES = [
    ('COMMAND', 'Command'),
    ('SENSOR', 'Sensor Data'),
    ('THRESHOLD', 'Threshold Violation'),
    ('AUTOMATION', 'Automation'),
    ('ERROR', 'Error'),
    ('INFO', 'Information'),
    ('WARNING', 'Warning'),
]

# Parameter Types for Thresholds
PARAMETER_CHOICES = [
    ('temperature', 'Temperature'),
    ('water_level', 'Water Level'),
    ('feed_level', 'Feed Level'),
    ('turbidity', 'Turbidity'),
    ('dissolved_oxygen', 'Dissolved Oxygen'),
    ('ph', 'pH'),
    ('ammonia', 'Ammonia'),
    ('battery', 'Battery'),
]

# Automation Actions
AUTOMATION_ACTIONS = [
    ('FEED', 'Feed'),
    ('WATER_DRAIN', 'Drain Water'),
    ('WATER_FILL', 'Fill Water'),
    ('WATER_FLUSH', 'Flush Water'),
    ('WATER_INLET_OPEN', 'Open Water Inlet'),
    ('WATER_INLET_CLOSE', 'Close Water Inlet'),
    ('WATER_OUTLET_OPEN', 'Open Water Outlet'),
    ('WATER_OUTLET_CLOSE', 'Close Water Outlet'),
    ('ALERT', 'Send Alert'),
    ('NOTIFICATION', 'Send Notification'),
    ('LOG', 'Log Event'),
]

# Command Types
COMMAND_TYPES = [
    ('FEED', 'Feed Command'),
    ('WATER_DRAIN', 'Drain Water'),
    ('WATER_FILL', 'Fill Water'),
    ('WATER_FLUSH', 'Flush Water'),
    ('WATER_INLET_OPEN', 'Open Water Inlet'),
    ('WATER_INLET_CLOSE', 'Close Water Inlet'),
    ('WATER_OUTLET_OPEN', 'Open Water Outlet'),
    ('WATER_OUTLET_CLOSE', 'Close Water Outlet'),
    ('SET_THRESHOLD', 'Set Sensor Threshold'),
    ('FIRMWARE_UPDATE', 'Firmware Update'),
    ('RESTART', 'Device Restart'),
    ('CONFIG_UPDATE', 'Configuration Update'),
]

# Command Status
COMMAND_STATUS = [
    ('PENDING', 'Pending'),
    ('SENT', 'Sent'),
    ('ACKNOWLEDGED', 'Acknowledged'),
    ('COMPLETED', 'Completed'),
    ('FAILED', 'Failed'),
    ('TIMEOUT', 'Timeout'),
]

# Device Status
DEVICE_STATUS = [
    ('ONLINE', 'Online'),
    ('OFFLINE', 'Offline'),
    ('ERROR', 'Error'),
    ('MAINTENANCE', 'Maintenance'),
]

# User Roles
USER_ROLES = [
    ('OWNER', 'Owner'),
    ('ADMIN', 'Administrator'),
    ('OPERATOR', 'Operator'),
    ('VIEWER', 'Viewer'),
]

# Notification Types
NOTIFICATION_TYPES = [
    ('EMAIL', 'Email'),
    ('SMS', 'SMS'),
    ('PUSH', 'Push Notification'),
    ('WEBHOOK', 'Webhook'),
]

# Threshold Operators
THRESHOLD_OPERATORS = [
    ('GT', 'Greater Than'),
    ('LT', 'Less Than'),
    ('GTE', 'Greater Than or Equal'),
    ('LTE', 'Less Than or Equal'),
    ('EQ', 'Equal'),
    ('NE', 'Not Equal'),
]

# Data Export Formats
EXPORT_FORMATS = [
    ('CSV', 'CSV'),
    ('JSON', 'JSON'),
    ('EXCEL', 'Excel'),
    ('PDF', 'PDF'),
]

# Time Intervals
TIME_INTERVALS = [
    ('1m', '1 Minute'),
    ('5m', '5 Minutes'),
    ('15m', '15 Minutes'),
    ('30m', '30 Minutes'),
    ('1h', '1 Hour'),
    ('6h', '6 Hours'),
    ('12h', '12 Hours'),
    ('1d', '1 Day'),
    ('1w', '1 Week'),
    ('1M', '1 Month'),
]
