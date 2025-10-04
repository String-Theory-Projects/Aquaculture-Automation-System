# Manual migration to sync with current database state

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("automation", "0002_alter_automationexecution_action_and_more"),
    ]

    operations = [
        # Add action field - it already exists in database but Django doesn't know
        migrations.AddField(
            model_name="automationschedule",
            name="action",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("FEED", "Feed"),
                    ("WATER_DRAIN", "Drain Water"),
                    ("WATER_FILL", "Fill Water"),
                    ("WATER_FLUSH", "Flush Water"),
                    ("WATER_INLET_OPEN", "Open Water Inlet"),
                    ("WATER_INLET_CLOSE", "Close Water Inlet"),
                    ("WATER_OUTLET_OPEN", "Open Water Outlet"),
                    ("WATER_OUTLET_CLOSE", "Close Water Outlet"),
                    ("ALERT", "Send Alert"),
                    ("NOTIFICATION", "Send Notification"),
                    ("LOG", "Log Event"),
                ],
                default="FEED",
                help_text="Specific action to perform when this schedule executes"
            ),
        ),
        # Update other fields to match current state
        migrations.AlterField(
            model_name="automationschedule",
            name="drain_water_level",
            field=models.FloatField(
                blank=True,
                help_text="Water level to drain to",
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(100),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="devicecommand",
            name="command_type",
            field=models.CharField(
                choices=[
                    ("FEED", "Feed Command"),
                    ("WATER_DRAIN", "Drain Water"),
                    ("WATER_FILL", "Fill Water"),
                    ("WATER_FLUSH", "Flush Water"),
                    ("WATER_INLET_OPEN", "Open Water Inlet"),
                    ("WATER_INLET_CLOSE", "Close Water Inlet"),
                    ("WATER_OUTLET_OPEN", "Open Water Outlet"),
                    ("WATER_OUTLET_CLOSE", "Close Water Outlet"),
                    ("SET_THRESHOLD", "Set Sensor Threshold"),
                    ("FIRMWARE_UPDATE", "Firmware Update"),
                    ("RESTART", "Device Restart"),
                    ("CONFIG_UPDATE", "Configuration Update"),
                ],
                max_length=20,
            ),
        ),
    ]
