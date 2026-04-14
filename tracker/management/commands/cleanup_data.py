import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from tracker.models import Session, Event
from datetime import timedelta
from django.db import connection

class Command(BaseCommand):
    help = 'Cleanup old session and event data to optimize database size (Retention: 7 days)'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7, help='Retention period in days')

    def handle(self, *args, **options):
        days = options['days']
        cutoff = timezone.now() - timedelta(days=days)

        self.stdout.write(f"Starting cleanup of data older than {cutoff} ({days} days)...")

        # 1. Delete events older than cutoff
        events_deleted, _ = Event.objects.filter(timestamp__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {events_deleted} old events."))

        # 2. Delete sessions older than cutoff
        sessions_deleted, _ = Session.objects.filter(started_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {sessions_deleted} old sessions."))

        # 3. Compacting database (SQLite VACUUM)
        self.stdout.write("Compacting database (VACUUM)...")
        with connection.cursor() as cursor:
            cursor.execute("VACUUM")
        
        # 4. Check final size
        db_path = connection.settings_dict['NAME']
        try:
            if os.path.exists(db_path):
                final_size = os.path.getsize(db_path) / (1024 * 1024)
                self.stdout.write(self.style.SUCCESS(f"Cleanup complete. New DB size: {final_size:.2f} MB"))
            else:
                self.stdout.write(self.style.WARNING("Database path not found for size check."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not check DB size: {e}"))
