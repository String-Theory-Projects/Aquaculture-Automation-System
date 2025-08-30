from django.core.management.base import BaseCommand
from automation.models import FeedStat, FeedStatHistory
from datetime import date, timedelta

class Command(BaseCommand):
    help = 'Rolls over stats at the start of new week/month/year'

    def handle(self, *args, **kwargs):
        today = date.today()

        rollovers = []

        if today.weekday() == 6:  # Sunday
            rollovers.append('weekly')
        if today.day == 1:
            rollovers.append('monthly')
        if today.month == 1 and today.day == 1:
            rollovers.append('yearly')

        for stat_type in rollovers:
            expiring_stats = FeedStat.objects.filter(stat_type=stat_type)
            for stat in expiring_stats:
                FeedStatHistory.objects.create(
                    user=stat.user,
                    stat_type=stat.stat_type,
                    amount=stat.amount,
                    start_date=stat.start_date,
                    end_date=today - timedelta(days=1)
                )
                # Reset for new cycle
                stat.amount = 0
                stat.start_date = today
                stat.save()

        self.stdout.write("Rollover complete.")
