# ISPON website: security guide

**Honest limits first.** No website can be made impossible to break into. What this project does is stack many independent defences so that an attacker has to beat all of them, and it proves the important ones with automated tests. The things software cannot protect against are: a weak or shared hosting server, a staff member being tricked into giving away a password or approving a fake 2FA prompt, a stolen laptop or phone, and brand-new unknown flaws in Django, Wagtail or the server itself. The checklist at the end covers the human and hosting side.

## What is built in (and tested)
| Area | Protection |
|---|---|
| Staff sign-in | **Two-factor authentication required** for every editor in production (authenticator app + backup codes). Passwords need 14+ characters, not common, not numeric-only, not similar to the account details, and are stored with **Argon2**. |
| Brute force | **5 failed sign-ins lock the address and the username for 1 hour** (django-axes). Failures are logged. |
| Admin exposure | The built-in Django admin is **switched off**. The CMS path can be changed with `DJANGO_ADMIN_PATH` so it is not the default `/admin/`. Admin pages are never cached or indexed and send their own CSP. |
| Sessions and cookies | Session cookie: `HttpOnly`, `SameSite=Strict`, `Secure`, `__Host-` prefixed, ends after **2 hours idle** or when the browser closes. CSRF cookie: `HttpOnly`, `SameSite=Lax`, `Secure`, `__Host-`, session-only. Visitors only ever receive the CSRF cookie. |
| Browser protections | **Content-Security-Policy** with `script-src 'self'` (no inline scripts, no third-party scripts), `frame-ancestors 'none'`, `object-src 'none'`, `form-action 'self'`, upgrade-insecure-requests; plus HSTS (1 year), `X-Frame-Options: DENY`, `nosniff`, strict Referrer-Policy, Permissions-Policy (camera, microphone, location, payment... off), COOP/CORP. No third-party requests at all (fonts are self-hosted, no analytics). |
| Injection | Django ORM only (no raw SQL); every template output is auto-escaped; JSON-LD is escaped for `<`, `>` and `&`; rich text is limited to a safe set of features. Tested with XSS and SQL-injection probes. |
| CSRF and hosts | CSRF checked on every POST (tested); `ALLOWED_HOSTS` enforced (a fake `Host` header gets 400). |
| Abuse and scanners | Per-address request limits (240 page views/min, 30 posts/min) with `429` and `Retry-After`; probes for `wp-login.php`, `.env`, `.git`, `phpmyadmin`, `*.php` and similar get `404` and **5 probes earn a one-hour ban**. Contact form: honeypot, consent box, 5 messages/hour. Newsletter: double opt-in, honeypot, rate limit, no email enumeration. |
| Uploads | Images and documents validated by content, not filename; allowed types are a short list (images, PDF/Office, MP4/WebM); no HTML/SVG/PHP/JS/EXE; size limits; identical files de-duplicated; `deploy/media.htaccess` stops anything in `media/` from running. |
| Errors | Custom 404 and 500 pages show nothing technical; `DEBUG` is refused on a public host; the site **refuses to start** with a weak `DJANGO_SECRET_KEY`. |
| Data minimisation | Contact messages deleted after 24 months, unsubscribed addresses after 12 months, unconfirmed addresses after 30 days (`purge_old_data`). Gravatar and all other third-party calls are disabled. |
| Logging | `logs/security.log` (rotating, 5 x 5 MB): failed sign-ins, lockouts, scanner probes, bans, rate-limit hits. No passwords or message text. Wagtail's Reports > Site history records who changed which page. |
| Disclosure | `/.well-known/security.txt` (RFC 9116) tells researchers how to report a problem. |
| Dependencies | `pip-audit` on the pinned requirements: **no known vulnerabilities**. `bandit` static scan: no medium or high findings. `manage.py check --deploy` shows only two deliberate opt-in HSTS notes. |

## Do these before launch
1. **Environment** (`.env`, never in the web root): a random `DJANGO_SECRET_KEY` of 64+ characters (`python -c "import secrets;print(secrets.token_urlsafe(64))"`), `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, database and email settings. Optional: `DJANGO_ADMIN_PATH=some-long-random-word`.
2. **HTTPS first**: turn on AutoSSL, confirm the site loads over HTTPS, then deploy. Raise `DJANGO_HSTS_SECONDS` only after it works (default is one year). Consider `DJANGO_HSTS_SUBDOMAINS=1` only if every subdomain is HTTPS, and `DJANGO_HSTS_PRELOAD=1` only if you want the browser preload list (hard to undo).
3. **Files**: copy `deploy/media.htaccess` to `media/.htaccess`; add the lines in `deploy/public_html.htaccess` to the domain's `.htaccess`; keep the project, `.env`, `db.sqlite3` (if used) and `logs/` outside `public_html` or denied (the project root should not be web-readable). Set file permissions: folders 755, files 644, `.env` and `deploy/backup.sh` 600/700.
4. **First sign-in**: create the administrator (`createsuperuser`, 14+ character password), sign in, and scan the QR code with an authenticator app. Save the backup codes offline. Every other editor does the same on first sign-in. Lost phone: another administrator removes the device (Settings > Users, or `python manage.py shell` and delete the user's `TOTPDevice`).
5. **Proxy**: if a proxy/CDN sits in front of the site, set `DJANGO_PROXY_COUNT` to the number of proxies so limits and bans use real visitor addresses (wrong values let attackers spoof their address).
6. **Cron jobs**: daily `python manage.py purge_old_data`; nightly `deploy/backup.sh` (edit paths; optional GPG encryption); every 5 minutes `send_newsletters`.
7. **Accounts**: one named account per person, least-privilege roles (`setup_roles`), remove accounts when people leave, no shared logins.
8. **Updates**: monthly `pip install -U -r requirements.txt` in a copy first, `pip-audit -r requirements.txt`, run the tests, then deploy. Subscribe to Django and Wagtail security announcements.
9. **Host**: keep PHP/Python versions current, enable the host's firewall/ModSecurity, turn off directory listing and unused FTP, use SFTP/SSH keys, enable the host's malware scanner. Consider Cloudflare (free plan) in front for DDoS and bot filtering.
10. **Legal**: have counsel review the Privacy Policy, Cookie Policy and Terms (they describe what this site actually does), confirm where the host's servers are, name a data protection contact, and check whether ISPON must register with the Nigeria Data Protection Commission.

## Backups and recovery
`deploy/backup.sh` dumps the database and archives `media/`; test a restore on a spare copy at least once (database: `psql`/`mysql < dump.sql` or copy `db.sqlite3`; media: untar into `media/`). Keep copies off the server.

## If you suspect a break-in
Change `DJANGO_SECRET_KEY` (signs everyone out), reset all editor passwords and 2FA devices, read `logs/security.log` and Wagtail Reports > Site history, restore from a clean backup if pages were altered, update everything, and tell affected people if their data was involved (the NDPA has notification duties).

## Testing it yourself
`DJANGO_DEBUG=1 python manage.py test apps.core.test_security` runs the security tests (headers and CSP, inline-script ban, XSS and SQL probes, CSRF, host header, throttling, scanner bans, lockout, cookie flags, 2FA enforcement, upload rules, data deletion, production settings). `pip-audit -r requirements.txt`, `bandit -r apps config` and `python manage.py check --deploy` should be run before every release.
