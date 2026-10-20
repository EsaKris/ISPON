"""Building and sending newsletter emails. Sending is never assumed: callers get a success flag."""
import logging
import re

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags

log = logging.getLogger(__name__)


def absolute(path):
    return settings.SITE_URL.rstrip("/") + path


def text_from_html(html):
    html = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"\2 (\1)", html, flags=re.S)
    html = re.sub(r"</(p|h\d|li|div)>", "\n\n", html)
    html = re.sub(r"<br\s*/?>", "\n", html)
    return re.sub(r"\n{3,}", "\n\n", strip_tags(html)).strip()


def _site():
    from apps.core.models import SiteSettings

    return SiteSettings.objects.first() or SiteSettings()


def send_confirmation(sub):
    url = absolute(reverse("subscriptions:confirm", args=[sub.token]))
    ctx = {"url": url, "site": _site(), "unsubscribe_url": absolute(reverse("subscriptions:unsubscribe", args=[sub.token]))}
    html = render_to_string("subscriptions/email/confirm.html", ctx)
    msg = EmailMultiAlternatives("Confirm your subscription to ISPON updates", text_from_html(html), settings.DEFAULT_FROM_EMAIL, [sub.email])
    msg.attach_alternative(html, "text/html")
    try:
        msg.send()
        return True
    except Exception:  # SMTP down, bad credentials, timeout...
        log.exception("Could not send confirmation email")
        return False


def build_newsletter_email(newsletter, to_email, unsubscribe_url, one_click_url=None):
    html = render_to_string("subscriptions/email/newsletter.html", {"newsletter": newsletter, "unsubscribe_url": unsubscribe_url, "site": _site()})
    msg = EmailMultiAlternatives(newsletter.subject, text_from_html(html) + f"\n\nUnsubscribe: {unsubscribe_url}", settings.DEFAULT_FROM_EMAIL, [to_email])
    msg.attach_alternative(html, "text/html")
    if one_click_url:
        msg.extra_headers["List-Unsubscribe"] = f"<{one_click_url}>"
        msg.extra_headers["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    return msg
