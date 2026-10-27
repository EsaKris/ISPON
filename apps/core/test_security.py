"""Security tests: headers, CSP, XSS/SQLi probes, CSRF, host header, brute force, throttling, cookies, 2FA, retention and production settings."""
import json
import os
import re
import secrets
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, override_settings
from django.utils import timezone

from apps.core.tests import Base
from apps.organisation.models import ContactSubmission
from apps.subscriptions.models import Subscriber

BASE_DIR = Path(settings.BASE_DIR)
PUBLIC = ["/", "/blog/", "/blog/ispon-anambra-state-branch-is-a-goal/", "/about-us/", "/contact-page/", "/gallery/", "/membership-procedure/", "/team/",
          "/services/", "/faq/", "/careers/", "/privacy-policy/", "/cookie-policy/", "/terms-of-use/", "/search/?q=x"]


def prod_env(**extra):
    env = {**os.environ, "DJANGO_DEBUG": "0", "DJANGO_SECRET_KEY": secrets.token_urlsafe(64), "DJANGO_ALLOWED_HOSTS": "ispon.gov.ng",
           "DB_ENGINE": "sqlite", "DJANGO_SETTINGS_MODULE": "config.settings"}
    env.update(extra)
    return env


class HeaderTests(Base):
    def test_strict_headers_on_every_public_page(self):
        for url in PUBLIC:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
            csp = r["Content-Security-Policy"]
            script = [d for d in csp.split("; ") if d.startswith("script-src")][0]
            self.assertEqual(script, "script-src 'self'", url)
            for needle in ["frame-ancestors 'none'", "object-src 'none'", "base-uri 'self'", "form-action 'self'", "default-src 'self'", "frame-src 'none'"]:
                self.assertIn(needle, csp, url)
            self.assertEqual(r["X-Frame-Options"], "DENY")
            self.assertEqual(r["X-Content-Type-Options"], "nosniff")
            self.assertEqual(r["Referrer-Policy"], "strict-origin-when-cross-origin")
            self.assertEqual(r["Cross-Origin-Opener-Policy"], "same-origin")
            self.assertIn("camera=()", r["Permissions-Policy"])
            self.assertIn("no-cache", r["Cache-Control"])

    def test_admin_gets_its_own_policy_and_is_not_cacheable_or_indexable(self):
        r = self.client.get("/admin/login/")
        self.assertEqual(r["X-Frame-Options"], "SAMEORIGIN")
        self.assertIn("no-store", r["Cache-Control"])
        self.assertIn("noindex", r["X-Robots-Tag"])
        self.assertIn("frame-ancestors 'self'", r["Content-Security-Policy"])

    def test_public_pages_have_no_inline_script_handlers_or_javascript_urls(self):
        for url in PUBLIC:
            h = self.client.get(url).content.decode()
            for tag in re.findall(r"<script\b[^>]*>", h):
                self.assertTrue("src=" in tag or "application/ld+json" in tag, f"{url}: inline script {tag}")
            self.assertIsNone(re.search(r"\son[a-z]+\s*=", h), url)
            self.assertNotIn("javascript:", h.lower(), url)
            self.assertNotIn("<style", h.lower(), url)  # only external CSS and style attributes

    def test_no_third_party_requests(self):
        for url in PUBLIC:
            h = self.client.get(url).content.decode()
            for tag in re.findall(r'<(?:script|img|iframe|video|source)\b[^>]*>|<link\b[^>]*rel="(?:stylesheet|preload|preconnect)"[^>]*>', h):
                self.assertNotRegex(tag, r'(?:src|href)="(?:https?:)?//', f"{url}: {tag[:100]}")

    def test_security_txt_robots_and_django_admin_off(self):
        t = self.client.get("/.well-known/security.txt").content.decode()
        self.assertIn("Contact: mailto:info@ispon.gov.ng", t)
        self.assertRegex(t, r"Expires: 20\d\d-")
        robots = self.client.get("/robots.txt").content.decode()
        self.assertIn("Disallow: /admin/", robots)
        self.assertEqual(self.client.get("/django-admin/").status_code, 404)


class InjectionTests(Base):
    def test_reflected_xss_is_escaped(self):
        payload = "<script>alert(1)</script>"
        for url in [f"/search/?q={payload}", f"/blog/?q={payload}", f"/blog/?tag={payload}", f"/gallery/?album={payload}", f"/contact-page/?q={payload}&state={payload}"]:
            h = self.client.get(url).content.decode()
            self.assertNotIn(payload, h, url)

    def test_stored_xss_in_contact_message_is_never_rendered_publicly(self):
        self.client.post("/contact-page/", {"name": "<b>x</b>", "email": "a@example.com", "subject": "<script>alert(1)</script>", "message": "<img src=x onerror=alert(1)>", "consent": "on"})
        self.assertNotIn("onerror", self.client.get("/contact-page/").content.decode())

    def test_sql_injection_probes_do_not_break_queries(self):
        for url in ["/search/?q=' OR 1=1 --", "/blog/?category=1' OR '1'='1", "/blog/?page=1;DROP TABLE auth_user", "/contact-page/?state=Abia'--", "/gallery/?album=%27%20OR%201=1"]:
            self.assertIn(self.client.get(url).status_code, (200, 404), url)
        self.assertTrue(get_user_model().objects.model._meta.db_table)

    def test_csrf_is_enforced_on_forms(self):
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.post("/contact-page/", {"name": "x"}).status_code, 403)
        self.assertEqual(c.post("/newsletter/subscribe/", {"email": "a@example.com", "consent": "on"}).status_code, 403)

    def test_bad_host_header_is_rejected(self):
        self.assertEqual(self.client.get("/", HTTP_HOST="evil.example.com").status_code, 400)

    def test_contact_form_requires_privacy_consent(self):
        r = self.client.post("/contact-page/", {"name": "Ada", "email": "ada@example.com", "subject": "Hi", "message": "Hello"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ContactSubmission.objects.count(), 0)
        self.assertContains(r, "Privacy Policy")

    def test_custom_404_does_not_leak_internals(self):
        r = self.client.get("/definitely-missing/")
        h = r.content.decode()
        self.assertEqual(r.status_code, 404)
        self.assertIn("Page not found", h)
        for leak in ["Traceback", "SECRET_KEY", "settings.py", "Django", "Wagtail"]:
            self.assertNotIn(leak, h)


@override_settings(RATE_LIMIT_ENABLED=True, RATE_LIMIT_GET=5, RATE_LIMIT_POST=3)
class ThrottleTests(Base):
    def test_too_many_requests_get_429(self):
        codes = [self.client.get("/faq/").status_code for _ in range(8)]
        self.assertEqual(codes[:5], [200] * 5)
        self.assertEqual(codes[5], 429)
        self.assertEqual(self.client.get("/faq/")["Retry-After"], "60")

    def test_posts_have_a_tighter_limit(self):
        codes = [self.client.post("/newsletter/subscribe/", {"email": f"a{i}@example.com", "consent": "on"}).status_code for i in range(5)]
        self.assertIn(429, codes)

    def test_scanner_probes_get_404_then_a_ban(self):
        for _ in range(5):
            self.assertEqual(self.client.get("/wp-login.php").status_code, 404)
        self.assertEqual(self.client.get("/").status_code, 429)  # banned: even normal pages are refused
        self.assertEqual(self.client.get("/.env").status_code, 404)

    def test_admin_is_exempt_from_the_page_limit(self):
        for _ in range(12):
            self.assertNotEqual(self.client.get("/admin/login/").status_code, 429)


class LoginSecurityTests(Base):
    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_superuser("root", "root@example.com", "Correct-horse-battery-9!")

    def attempt(self, password):
        return self.client.post("/admin/login/", {"username": "root", "password": password})

    def test_lockout_after_five_failed_sign_ins_even_with_the_right_password(self):
        for _ in range(4):
            self.assertNotEqual(self.attempt("wrong").status_code, 429)
        self.assertEqual(self.attempt("wrong").status_code, 429)  # the fifth failure locks the account and address
        self.assertEqual(self.attempt("Correct-horse-battery-9!").status_code, 429)

    def test_successful_sign_in_sets_hardened_session_cookie(self):
        r = self.attempt("Correct-horse-battery-9!")
        self.assertEqual(r.status_code, 302)
        c = r.cookies["sessionid"]
        self.assertTrue(c["httponly"])
        self.assertEqual(c["samesite"], "Strict")

    def test_csrf_cookie_is_httponly_lax_and_session_only(self):
        r = self.client.get("/contact-page/")
        c = r.cookies["csrftoken"]
        self.assertTrue(c["httponly"])
        self.assertEqual(c["samesite"], "Lax")
        self.assertEqual(c["max-age"], "")
        self.assertEqual(c["expires"], "")

    def test_passwords_are_stored_with_argon2(self):
        self.assertTrue(self.user.password.startswith("argon2$"))

    def test_weak_passwords_are_refused(self):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        for bad in ["short1", "password", "12345678901234", "root"]:
            with self.assertRaises(ValidationError):
                validate_password(bad, self.user)

    @override_settings(WAGTAIL_2FA_REQUIRED=True)
    def test_two_factor_setup_is_forced_for_editors(self):
        self.client.force_login(self.user)
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("2fa", r["Location"])
        self.assertEqual(self.client.get("/admin/pages/").status_code, 302)

    def test_editors_cannot_upload_scripts_as_documents(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(self.user)
        for name in ["evil.html", "evil.php", "evil.svg", "evil.js", "evil.exe"]:
            r = self.client.post("/admin/documents/multiple/add/", {"title": name, "files[]": SimpleUploadedFile(name, b"<script>alert(1)</script>", "text/html")})
            self.assertFalse(json.loads(r.content).get("success", False), name)


class RetentionTests(Base):
    def test_purge_deletes_only_old_data(self):
        from django.core.management import call_command
        old = timezone.now() - timedelta(days=800)
        ContactSubmission.objects.create(name="old", email="o@example.com", subject="s", message="m")
        ContactSubmission.objects.create(name="new", email="n@example.com", subject="s", message="m")
        ContactSubmission.objects.filter(name="old").update(created_at=old)
        Subscriber.objects.create(email="gone@example.com", is_active=False, unsubscribed_at=timezone.now() - timedelta(days=400))
        Subscriber.objects.create(email="recent-unsub@example.com", is_active=False, unsubscribed_at=timezone.now() - timedelta(days=5))
        Subscriber.objects.create(email="stale@example.com")
        Subscriber.objects.filter(email="stale@example.com").update(consented_at=timezone.now() - timedelta(days=45))
        Subscriber.objects.create(email="fresh@example.com")
        call_command("purge_old_data", "--dry-run")
        self.assertEqual(ContactSubmission.objects.count(), 2)
        call_command("purge_old_data")
        self.assertEqual(list(ContactSubmission.objects.values_list("name", flat=True)), ["new"])
        self.assertEqual(sorted(Subscriber.objects.values_list("email", flat=True)), ["fresh@example.com", "recent-unsub@example.com"])

    def test_legal_pages_exist_match_retention_and_are_linked(self):
        p = self.client.get("/privacy-policy/").content.decode()
        for needle in ["Nigeria Data Protection Act 2023", "24 months", "12 months", "30 days", "NDPC", "info@ispon.gov.ng"]:
            self.assertIn(needle.replace("'", "&#x27;"), p)
        c = self.client.get("/cookie-policy/").content.decode()
        for needle in ["csrftoken", "sessionid", "ispon-notice", "strictly necessary"]:
            self.assertIn(needle, c)
        self.assertIn("Governing law", self.client.get("/terms-of-use/").content.decode())
        home = self.client.get("/").content.decode()
        for href in ['href="/privacy-policy/"', 'href="/cookie-policy/"', 'href="/terms-of-use/"']:
            self.assertIn(href, home)
        self.assertIn('id="cookie-note"', home)


class ProductionSettingsTests(Base):
    """Starts a separate Python with production settings and checks the values a live site would use."""

    def run_py(self, code, **env):
        return subprocess.run([sys.executable, "-c", code], cwd=BASE_DIR, env=prod_env(**env), capture_output=True, text=True, timeout=120)

    def test_production_cookie_hsts_and_hasher_settings(self):
        out = self.run_py("import django,json;django.setup();from django.conf import settings as s;"
                          "print(json.dumps({k:getattr(s,k) for k in ['SESSION_COOKIE_SECURE','CSRF_COOKIE_SECURE','SESSION_COOKIE_NAME','CSRF_COOKIE_NAME','SECURE_SSL_REDIRECT','SECURE_HSTS_SECONDS','DEBUG','WAGTAIL_2FA_REQUIRED','RATE_LIMIT_ENABLED','SESSION_COOKIE_SAMESITE','ENABLE_DJANGO_ADMIN']}))")
        self.assertEqual(out.returncode, 0, out.stderr[-800:])
        v = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertTrue(v["SESSION_COOKIE_SECURE"] and v["CSRF_COOKIE_SECURE"] and v["SECURE_SSL_REDIRECT"])
        self.assertEqual((v["SESSION_COOKIE_NAME"], v["CSRF_COOKIE_NAME"]), ("__Host-sessionid", "__Host-csrftoken"))
        self.assertGreaterEqual(v["SECURE_HSTS_SECONDS"], 31536000)
        self.assertFalse(v["DEBUG"] or v["ENABLE_DJANGO_ADMIN"])
        self.assertTrue(v["WAGTAIL_2FA_REQUIRED"] and v["RATE_LIMIT_ENABLED"])
        self.assertEqual(v["SESSION_COOKIE_SAMESITE"], "Strict")

    def test_weak_or_missing_secret_key_stops_the_site(self):
        for key in ["short", "dev-only-insecure-key" + "x" * 40, "change-me-to-a-long-random-string"]:
            self.assertNotEqual(self.run_py("import django;django.setup()", DJANGO_SECRET_KEY=key).returncode, 0, key)

    def test_debug_refused_on_a_public_host(self):
        self.assertNotEqual(self.run_py("import django;django.setup()", DJANGO_DEBUG="1", DJANGO_ALLOWED_HOSTS="ispon.gov.ng").returncode, 0)

    def test_django_deploy_check_only_has_the_two_documented_warnings(self):
        r = subprocess.run([sys.executable, "manage.py", "check", "--deploy"], cwd=BASE_DIR, env=prod_env(), capture_output=True, text=True, timeout=120)
        codes = set(re.findall(r"security\.W\d+", r.stdout + r.stderr))
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        self.assertLessEqual(codes, {"security.W005", "security.W021"})  # HSTS subdomains/preload are deliberate opt-ins
