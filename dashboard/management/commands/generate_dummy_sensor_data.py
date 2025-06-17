import math
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from dashboard.models import Pond, SensorData


class Command(BaseCommand):
    help = "Generates dummy sensor data for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "pond_id", type=int, help="ID of the pond to generate data for"
        )
        parser.add_argument(
            "--days",
            type=int,
            default=60,
            help="Number of days of historical data to generate",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing sensor data for the pond before generating new data",
        )

    def handle(self, *args, **kwargs):
        pond_id = kwargs["pond_id"]
        days = kwargs["days"]
        clear_data = kwargs["clear"]

        try:
            pond = Pond.objects.get(id=pond_id)
        except Pond.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Pond with ID {pond_id} does not exist")
            )
            return

        if clear_data:
            deleted_count, _ = SensorData.objects.filter(pond=pond).delete()
            self.stdout.write(
                self.style.SUCCESS(f"Cleared {deleted_count} existing sensor readings")
            )

        # Generate data points
        end_time = timezone.now()
        start_time = end_time - timedelta(days=days)

        # Base values for parameters
        base_values = {
            "temperature": 25.0,  # °C
            "water_level": 85.0,  # %
            "turbidity": 10.0,  # NTU
            "dissolved_oxygen": 7.5,  # mg/L
            "ph": 7.2,  # pH scale
            "feed_level": 100.0,  # %
        }

        # Create data points in batches
        batch_size = 1000
        data_points = []
        hour_count = 0
        current_time = start_time

        self.stdout.write(f"Generating sensor data from {start_time} to {end_time}")

        with transaction.atomic():
            while current_time <= end_time:
                # Daily and hourly variation factors
                day_factor = math.sin(hour_count / 24 * math.pi) * 0.5  # Daily cycle
                hour_factor = math.sin(hour_count * 0.261799)  # ~24 hour cycle

                # Generate sensor reading with realistic variations
                data_point = SensorData(
                    pond=pond,
                    timestamp=current_time,
                    temperature=self.clamp(
                        base_values["temperature"]
                        + day_factor
                        + random.uniform(-0.5, 0.5),
                        20,
                        30,
                    ),
                    water_level=self.clamp(
                        base_values["water_level"]
                        - (hour_count * 0.02) % 15
                        + random.uniform(-0.5, 0.5),
                        0,
                        100,
                    ),
                    turbidity=self.clamp(
                        base_values["turbidity"] + random.uniform(-2, 2), 0, 1000
                    ),
                    dissolved_oxygen=self.clamp(
                        base_values["dissolved_oxygen"]
                        + hour_factor * 0.3
                        + random.uniform(-0.2, 0.2),
                        0,
                        20,
                    ),
                    ph=self.clamp(
                        base_values["ph"] + random.uniform(-0.1, 0.1), 6.5, 8.5
                    ),
                    feed_level=self.clamp(
                        base_values["feed_level"]
                        - (hour_count * 0.1) % 50
                        + random.uniform(-1, 1),
                        0,
                        100,
                    ),
                )

                data_points.append(data_point)
                hour_count += 1
                current_time += timedelta(hours=1)

                # Bulk create when batch size is reached
                if len(data_points) >= batch_size:
                    SensorData.objects.bulk_create(data_points)
                    data_points = []
                    self.stdout.write(
                        self.style.SUCCESS(f"Generated {hour_count} data points...")
                    )

            # Create any remaining data points
            if data_points:
                SensorData.objects.bulk_create(data_points)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully generated {hour_count} sensor readings for pond "{pond.name}"'
            )
        )

    def clamp(self, value, min_value, max_value):
        """Clamp a value between min and max values"""
        return max(min_value, min(max_value, value))
