from django import forms
from django.core.cache import cache
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .mail import send_confirmation
from .models import Subscriber

RESEND_AFTER = 300  # seconds


class SubscribeForm(forms.Form):
    email = forms.EmailField(max_length=254)
    consent = forms.BooleanField()
    website = forms.CharField(required=False)  # honeypot

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""


def _msg(request, text, status=200, token=None, confirm=None):
    return render(request, "subscriptions/message.html", {"message": text, "token": token, "confirm": confirm, "noindex": True, "seo_title": "Newsletter"}, status=status)


@require_POST
def subscribe(request):
    key = f"nl:{request.META.get('REMOTE_ADDR', '')}"
    n = cache.get(key, 0)
    if n >= 10:
        return _msg(request, "Too many attempts. Please try again later.", 429)
    cache.set(key, n + 1, 3600)
    form = SubscribeForm(request.POST)
    if not form.is_valid():
        return _msg(request, "Please enter a valid email address and tick the consent box.", 400)
    sub, created = Subscriber.objects.get_or_create(email=form.cleaned_data["email"])
    if not (sub.confirmed_at and sub.is_active):
        if not created and not sub.is_active:  # re-subscribing after unsubscribing needs a fresh confirmation
            sub.is_active, sub.unsubscribed_at, sub.confirmed_at = True, None, None
        recent = sub.confirmation_sent_at and (timezone.now() - sub.confirmation_sent_at).total_seconds() < RESEND_AFTER
        if not recent:
            if not send_confirmation(sub):
                sub.save()
                return _msg(request, "We could not send the confirmation email right now. Please try again later.", 503)
            sub.confirmation_sent_at = timezone.now()
        sub.save()
    # Same answer for every address, so this form cannot be used to discover who is subscribed.
    return _msg(request, "Almost done. If this address can be subscribed, we have sent it a confirmation link. Please check your inbox and spam folder.")


def confirm(request, token):
    sub = get_object_or_404(Subscriber, token=token)
    if request.method == "POST":  # a button press, so mail scanners that open links do not confirm for you
        sub.confirmed_at, sub.is_active, sub.unsubscribed_at = timezone.now(), True, None
        sub.save()
        return _msg(request, "Your subscription is confirmed. Thank you.")
    if sub.confirmed_at and sub.is_active:
        return _msg(request, "This address is already confirmed.")
    return _msg(request, "Confirm that you want to receive ISPON updates by email?", confirm=sub.token)


def unsubscribe(request, token):
    sub = get_object_or_404(Subscriber, token=token)
    if request.method == "POST":
        sub.is_active, sub.unsubscribed_at = False, timezone.now()
        sub.save()
        return _msg(request, "You have been unsubscribed.")
    return _msg(request, "Unsubscribe this address from ISPON updates?", token=sub.token)


@csrf_exempt
@require_POST
def one_click_unsubscribe(request, token):
    """Target of the List-Unsubscribe header (RFC 8058): mail apps POST here without a browser session."""
    sub = get_object_or_404(Subscriber, token=token)
    sub.is_active, sub.unsubscribed_at = False, timezone.now()
    sub.save()
    return _msg(request, "You have been unsubscribed.")
