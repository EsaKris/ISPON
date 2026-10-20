"""Send queued newsletters in small batches. Run from cron, for example every 5 minutes. Safe to re-run: nobody gets a newsletter twice."""
import time

from django.core.mail import get_connection
from django.core.management.base import BaseCommand
from django.urls import reverse
from django.utils import timezone

from apps.subscriptions.mail import absolute, build_newsletter_email
from apps.subscriptions.models import Newsletter, NewsletterDelivery


class Command(BaseCommand):
    help = "Send queued newsletters to confirmed, active subscribers."

    def add_arguments(self, parser):
        parser.add_argument("--batch", type=int, default=40, help="Maximum emails this run (stay under your host's hourly limit).")
        parser.add_argument("--delay", type=float, default=0, help="Seconds to wait between emails.")

    def handle(self, *args, **o):
        left, sent, failed = o["batch"], 0, 0
        conn = get_connection()
        for nl in Newsletter.objects.filter(status=Newsletter.QUEUED).order_by("queued_at"):
            for sub in nl.pending()[:left]:
                msg = build_newsletter_email(nl, sub.email, absolute(reverse("subscriptions:unsubscribe", args=[sub.token])),
                                             absolute(reverse("subscriptions:one_click", args=[sub.token])))
                msg.connection = conn
                try:
                    msg.send()
                    err = ""
                    sent += 1
                except Exception as e:
                    err, failed = str(e)[:200] or e.__class__.__name__, failed + 1
                NewsletterDelivery.objects.create(newsletter=nl, subscriber=sub, error=err)
                left -= 1
                if o["delay"]:
                    time.sleep(o["delay"])
            if not nl.pending().exists():
                nl.status, nl.sent_at = Newsletter.SENT, timezone.now()
                nl.save(update_fields=["status", "sent_at"])
            if left <= 0:
                break
        self.stdout.write(f"Sent {sent}, failed {failed}.")
