"""Delete personal data we no longer need (matches the Privacy Policy). Run daily from cron. Use --dry-run to preview."""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.organisation.models import ContactSubmission
from apps.subscriptions.models import Subscriber


class Command(BaseCommand):
    help = "Delete old contact messages and stale newsletter records."

    def add_arguments(self, parser):
        parser.add_argument("--contact-days", type=int, default=730, help="Delete contact messages older than this (default 730 = 24 months).")
        parser.add_argument("--unsubscribed-days", type=int, default=365, help="Delete unsubscribed addresses after this many days (default 12 months).")
        parser.add_argument("--unconfirmed-days", type=int, default=30, help="Delete addresses never confirmed after this many days.")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **o):
        now = timezone.now()
        qs = {
            "contact messages": ContactSubmission.objects.filter(created_at__lt=now - timedelta(days=o["contact_days"])),
            "unsubscribed addresses": Subscriber.objects.filter(is_active=False, unsubscribed_at__lt=now - timedelta(days=o["unsubscribed_days"])),
            "unconfirmed addresses": Subscriber.objects.filter(confirmed_at__isnull=True, consented_at__lt=now - timedelta(days=o["unconfirmed_days"])),
        }
        for label, q in qs.items():
            n = q.count()
            if not o["dry_run"]:
                q.delete()
            self.stdout.write(f"{'Would delete' if o['dry_run'] else 'Deleted'} {n} {label}.")
