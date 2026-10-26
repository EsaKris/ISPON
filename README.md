# ISPON website (Django 5.2 LTS + Wagtail 7.4)

Status: **all phases built; items marked "not verified" below still need a real-environment check.**
Built and tested (29 automated tests): Home, News and Blog (categories, tags, search, filters, pagination, featured post, scheduled publishing,
JSON-LD, sharing links, related posts, old dated URLs redirected), About, Membership Procedure, Contact + branch directory + form, Team, Gallery
(draggable wall + albums + viewer), newsletter (consent, duplicates, unsubscribe), site-wide search, roles, sitemap, robots, redirects.
Custom admin panel: dashboard quick actions, News and Photo albums menus, grouped People & contacts menu, bulk photo upload, ISPON colour accent (theme colour not visually checked).
Membership fees are structured records editable in the CMS.
SEO: title and description per page, canonical URLs, Open Graph and X cards (article image used for blog shares), geo tags, schema.org JSON-LD (Organization, WebSite, breadcrumbs, NewsArticle, ContactPage with branches, ImageGallery, team list), sitemap, dynamic robots.txt, RSS feed at /blog/feed/, web manifest, favicon from the uploaded logo, noindex on search, filters and newsletter pages. Not verified by a third-party validator (Google Rich Results Test, Search Console): run those after deployment.
Content from ispon.gov.ng (homepage, About, Membership, Contact, Team, Blog page 1) is loaded by `seed_site`.

**Not verified:** deployment on your cPanel account; browser tests (`tests_e2e/`, written but never run: no browser could be installed in the build sandbox);
WCAG audit with a real tool (only static checks run: lang, one h1, alt text, form labels, skip link); performance measurements; blog page 2 and the Gallery page of the old site were not read.
**Newsletter:** double opt-in (confirmation email), unsubscribe links and one-click unsubscribe, newsletters written and queued in the admin and sent in batches by a scheduled job. Needs working SMTP (see Email below). Sending has been tested with a test mail backend only, never against a real mail server.

## Design
Navy (#0A2540) and orange (#FF6B00) with DM Serif Display and DM Sans (self-hosted in `static/fonts`, no external font requests), rounded cards, pill buttons, a navigation bar that is transparent over the page's top band and turns solid on scroll, fade-up reveals, a countdown for upcoming events and a hero carousel. All styles are in `static/css/ispon.css`; colours are CSS variables at the top. The admin panel and its logo are themed to match. Generated starter pictures (news covers, team monograms, About and hero illustrations) were regenerated in the same palette.

## Local setup
```
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env           # set DJANGO_DEBUG=1 and DB_ENGINE=sqlite for local work
python manage.py migrate
python manage.py seed_site     # page tree + verified content from ispon.gov.ng
python manage.py setup_roles   # Content Administrator, Gallery Manager, Branch & Team Manager
python manage.py createsuperuser
python manage.py runserver     # site: /   CMS: /admin/
DJANGO_DEBUG=1 python manage.py test apps
# browser tests: see tests_e2e/test_site.py header
```
Team members are seeded **unpublished** until ISPON confirms who is shown (see checklist). Tick "published" in Snippets > Team members.

## Deploying on cPanel (check these with your host first)
cPanel support varies by plan. Before starting, confirm: **Setup Python App** exists (Passenger), Python 3.10+ is available (Django 5.2 needs 3.10+),
which database you get (PostgreSQL is preferred; many plans only offer MySQL/MariaDB, set `DB_ENGINE=mysql` and install `mysqlclient`; if it fails to build ask the host),
and that you have SSH or the Terminal tool. If any answer is no, the project cannot run there as-is.

1. cPanel > **Setup Python App**: choose Python 3.10+, application root `ispon`, domain `ispon.gov.ng`, startup file `passenger_wsgi.py`, entry point `application`.
2. Upload the project into the app root (not into `public_html`). In the app's virtualenv terminal: `pip install -r requirements.txt` plus your DB driver.
3. Create the database and user in cPanel (PostgreSQL or MySQL wizard). Add the environment variables from `.env.example` in the Python App screen, with a new long `DJANGO_SECRET_KEY`.
4. `python manage.py migrate && python manage.py seed_site && python manage.py setup_roles && python manage.py createsuperuser && python manage.py collectstatic --noinput`
5. Static files are served by WhiteNoise. For media, set `DJANGO_MEDIA_ROOT=/home/<user>/public_html/media` so Apache serves uploads directly.
6. Enable **AutoSSL**/Let's Encrypt for the domain. Keep `DJANGO_SSL_REDIRECT=1`. After HTTPS works, raise `DJANGO_HSTS_SECONDS`.
7. In the CMS open Settings > Sites and set the hostname to `ispon.gov.ng`. Restart the app from the Python App screen after every code or env change.
8. Backups: schedule a nightly database dump (cPanel Cron: `mysqldump` or `pg_dump`) and include `media/` in cPanel Backup. Restore by importing the dump and restoring `media/`.
9. Updating: upload code, `pip install -r requirements.txt`, `migrate`, `collectstatic`, restart.
Behind cPanel the visitor IP may be the proxy's, which makes the contact-form rate limit shared. Verify `REMOTE_ADDR` on your host.
Error logs: cPanel > Errors, or the `stderr.log` in the app root.

## Updating an existing site to the current design
The design lives in the templates and CSS, so every page picks it up as soon as the new code is live. Steps (local or cPanel terminal, with the virtualenv active):
1. Back up the database and `media/`.
2. Copy the new project files over the old ones (keep your `.env` and `media/`).
3. `pip install -r requirements.txt`
4. `python manage.py migrate`
5. `python manage.py upgrade_site` (creates the first hero slide from your existing hero text, converts an old plain About Us / Membership page to the designed page types, keeping the old one as an unpublished "-previous" draft; adds Services, Careers and FAQ; fills empty homepage sections and blank settings; never overwrites text you edited; safe to repeat).
6. `python manage.py collectstatic --noinput`, then restart the app (cPanel > Setup Python App > Restart) and hard-refresh the browser.
After step 5, copy any wording you had edited on the old About / Membership page from the "-previous" draft into the new page, then delete the draft.

## Pictures
`seed_site` loads generated starter artwork (news covers, team monogram portraits) from `seed_assets/` so nothing is empty. These are placeholders, not photographs.
To bring in the real pictures from the old ispon.gov.ng site (logo, the 14 team portraits, news pictures, the 10 gallery photos), run once on a machine or host with internet access, and only for pictures ISPON owns or may reuse: `python manage.py import_old_site_images` (use `--only logo,team,blog,gallery` to limit). It could not be run in the build sandbox (no access to the old site), so it is tested with a simulated download only.

## Email and newsletters (cPanel)
1. cPanel > Email Accounts: create `info@ispon.gov.ng` (or a `newsletter@` address). Put its details in the environment: `EMAIL_HOST=mail.ispon.gov.ng`, `EMAIL_PORT=465`, `EMAIL_USE_SSL=1` (or port 587 with `EMAIL_USE_SSL=0`), `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`, `SITE_URL=https://ispon.gov.ng`. Restart the app.
2. cPanel > Email Deliverability: make sure SPF and DKIM are valid for the domain, otherwise mail lands in spam.
3. Ask your host for the hourly sending limit (shared plans often allow 100-500 per hour). Choose `--batch` to stay under it.
4. cPanel > Cron Jobs, every 5 minutes: `cd ~/ispon && source ~/virtualenv/ispon/3.12/bin/activate && python manage.py send_newsletters --batch 40` (adjust the virtualenv path shown in the Python App screen).
5. Test: Admin > Send newsletters > "Send me a test", subscribe with your own address from the website footer, click the link in the confirmation email.
Large lists (thousands) are better sent through a dedicated mail service; this setup is meant for a modest list.

## Production checklist
`DJANGO_DEBUG=0`, unique secret key, allowed hosts, CSRF origins, HTTPS on, admin passwords 12+ chars, `python manage.py check --deploy`, backups tested, real logo uploaded in Settings > Site settings.
