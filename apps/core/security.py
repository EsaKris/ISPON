"""Security layer: response headers (CSP etc.), request throttling, scanner blocking and client IP handling."""
import logging
import re
import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

log = logging.getLogger("ispon.security")

PERMISSIONS_POLICY = "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=(), interest-cohort=(), browsing-topics=()"
SCANNER = re.compile(
    r"(wp-admin|wp-login|wp-content|wp-includes|xmlrpc|phpmyadmin|/\.env|/\.git|/\.svn|/\.ds_store|/\.aws|/\.ssh|/cgi-bin|/vendor/phpunit|/boaform|/actuator|"
    r"eval-stdin|\.(php\d?|asp|aspx|jsp|cgi|sql|bak|old|swp|ini|git|env)(/|$))"
)


def client_ip(request):
    """Client address. Behind exactly N trusted proxies (DJANGO_PROXY_COUNT) the Nth value from the right of X-Forwarded-For is used."""
    n = getattr(settings, "PROXY_COUNT", 0)
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if n and xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if len(parts) >= n:
            return parts[-n]
    return request.META.get("REMOTE_ADDR", "")


def axes_client_ip(request):
    return client_ip(request)


def _is_admin(path):
    admin = "/" + settings.ADMIN_URL.strip("/") + "/"
    return path.startswith(admin) or path.startswith("/django-admin/")


def build_csp(admin):
    if admin:  # the Wagtail editor needs inline scripts; it is only reachable after signing in
        parts = ["default-src 'self'", "script-src 'self' 'unsafe-inline'", "style-src 'self' 'unsafe-inline'", "img-src 'self' data: blob:", "font-src 'self' data:",
                 "media-src 'self' blob:", "connect-src 'self'", "frame-src 'self'", "frame-ancestors 'self'", "worker-src 'self' blob:", "object-src 'none'",
                 "base-uri 'self'", "form-action 'self'"]
    else:
        parts = ["default-src 'self'", "script-src 'self'", "style-src 'self'", "style-src-attr 'unsafe-inline'", "img-src 'self' data: blob:", "font-src 'self'",
                 "media-src 'self' https:", "connect-src 'self'", "frame-src 'none'", "frame-ancestors 'none'", "worker-src 'none'", "object-src 'none'",
                 "base-uri 'self'", "form-action 'self'", "manifest-src 'self'"]
    if not settings.DEBUG:
        parts.append("upgrade-insecure-requests")
    return "; ".join(parts)


class SecurityHeadersMiddleware:
    """Adds strict security headers to every response. Public pages get a script-free-of-inline CSP; the admin gets its own."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        admin = _is_admin(request.path)
        h = response.headers
        h["Content-Security-Policy"] = build_csp(admin)
        h["Permissions-Policy"] = PERMISSIONS_POLICY
        h["X-Frame-Options"] = "SAMEORIGIN" if admin else "DENY"
        h["X-Content-Type-Options"] = "nosniff"
        h["Cross-Origin-Opener-Policy"] = "same-origin"
        h.setdefault("Cross-Origin-Resource-Policy", "same-site")
        h["X-Permitted-Cross-Domain-Policies"] = "none"
        h["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if admin:
            h["X-Robots-Tag"] = "noindex, nofollow"
            h["Cache-Control"] = "no-store, private"
        elif "text/html" in response.get("Content-Type", ""):
            h.setdefault("Cache-Control", "private, no-cache")  # pages carry a per-visitor CSRF token
        return response


class ScannerBlockMiddleware:
    """Answers 404 to probes for WordPress, .env, .git, PHP etc. Repeated probes earn a temporary ban."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if SCANNER.search(request.path.lower()) and not request.path.startswith("/static/"):
            ip = client_ip(request)
            n = (cache.get(f"strikes:{ip}") or 0) + 1
            cache.set(f"strikes:{ip}", n, 3600)
            log.warning("scanner probe from %s: %s (strike %s)", ip, request.path[:120], n)
            if n >= getattr(settings, "STRIKE_LIMIT", 5):
                cache.set(f"ban:{ip}", 1, 3600)
                log.warning("temporarily banned %s", ip)
            return HttpResponse("Not found", status=404, content_type="text/plain")
        return self.get_response(request)


class RateLimitMiddleware:
    """Per-address request throttle (separate, tighter limit for POST). Banned addresses get 429 for an hour. The admin has its own login lockout."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.RATE_LIMIT_ENABLED or _is_admin(request.path) or request.path.startswith(("/static/", "/media/")):
            return self.get_response(request)
        ip = client_ip(request)
        if cache.get(f"ban:{ip}"):
            return self.too_many(ip, "banned")
        limit = settings.RATE_LIMIT_POST if request.method == "POST" else settings.RATE_LIMIT_GET
        key = f"rl:{ip}:{request.method == 'POST'}:{int(time.time() // 60)}"
        cache.add(key, 0, 75)
        try:
            n = cache.incr(key)
        except ValueError:
            n = 1
        if n > limit:
            return self.too_many(ip, f"rate limit ({n}/min)")
        return self.get_response(request)

    @staticmethod
    def too_many(ip, why):
        log.warning("429 for %s: %s", ip, why)
        r = HttpResponse("Too many requests. Please slow down and try again later.", status=429, content_type="text/plain")
        r["Retry-After"] = "60"
        return r
