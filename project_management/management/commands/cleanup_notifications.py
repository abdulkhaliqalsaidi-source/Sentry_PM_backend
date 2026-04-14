from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from project_management.models import Notification

class Command(BaseCommand):
    help = 'Cleans up old notifications to save database space (like Jira auto-archiving).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-read',
            type=int,
            default=30,
            help='Delete read notifications older than this many days (default 30)',
        )
        parser.add_argument(
            '--days-unread',
            type=int,
            default=90,
            help='Delete unread notifications older than this many days (default 90)',
        )

    def handle(self, *args, **options):
        days_read = options['days_read']
        days_unread = options['days_unread']

        now = timezone.now()
        read_threshold = now - timedelta(days=days_read)
        unread_threshold = now - timedelta(days=days_unread)

        # Delete old read notifications
        old_read = Notification.objects.filter(is_read=True, created_at__lt=read_threshold)
        read_count, _ = old_read.delete()

        # Delete old unread notifications
        old_unread = Notification.objects.filter(is_read=False, created_at__lt=unread_threshold)
        unread_count, _ = old_unread.delete()

        total = read_count + unread_count

        if total > 0:
            self.stdout.write(self.style.SUCCESS(
                f'Successfully deleted {total} old notifications '
                f'({read_count} read older than {days_read} days, {unread_count} unread older than {days_unread} days)'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('No old notifications found to clean up.'))
