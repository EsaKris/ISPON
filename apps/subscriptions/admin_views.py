"""Admin page to test, queue and monitor newsletters."""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from wagtail.admin.auth import require_admin_access

from .mail import absolute, build_newsletter_email
from .models import Newsletter


@require_admin_access
def manage(request):
    if not request.user.has_perm("subscriptions.change_newsletter"):
        raise PermissionDenied
    if request.method == "POST":
        nl, action = get_object_or_404(Newsletter, pk=request.POST.get("id")), request.POST.get("action")
        if action == "test":
            if not request.user.email:
                messages.error(request, "Add an email address to your account first (Account settings).")
            else:
                try:
                    build_newsletter_email(nl, request.user.email, absolute("/")).send()
                    messages.success(request, f"Test email sent to {request.user.email}.")
                except Exception as e:
                    messages.error(request, f"The test email could not be sent: {e}")
        elif action == "queue" and nl.status == Newsletter.DRAFT:
            if not nl.recipients().exists():
                messages.error(request, "There are no confirmed subscribers yet.")
            else:
                nl.status, nl.queued_at = Newsletter.QUEUED, timezone.now()
                nl.save(update_fields=["status", "queued_at"])
                messages.success(request, f"\u2018{nl.subject}\u2019 is queued. It is sent in batches by the scheduled job.")
        elif action == "cancel" and nl.status == Newsletter.QUEUED:
            nl.status = Newsletter.DRAFT
            nl.save(update_fields=["status"])
            messages.success(request, "Sending paused. Already-sent emails are not recalled; the rest are held.")
        return redirect(reverse("newsletter_manage"))
    rows = [{"nl": n, "recipients": n.recipients().count(), "sent": n.deliveries.filter(error="").count(),
             "failed": n.deliveries.exclude(error="").count(), "pending": n.pending().count()} for n in Newsletter.objects.all()[:50]]
    return render(request, "subscriptions/admin/newsletters.html", {"rows": rows})
