import datetime
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from wagtail.models import Page

from apps.core.models import AboutPage as AboutPage_, HomePage, Statistic
from apps.gallery.models import AlbumImage, AlbumPage, GalleryIndexPage
from apps.organisation.models import Branch, ContactSubmission, TeamMember


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_site")
        call_command("setup_roles")

    def setUp(self):
        cache.clear()


class PublicUrlTests(Base):
    def test_required_urls(self):
        for url in ["/", "/about-us/", "/contact-page/", "/gallery/", "/membership-procedure/", "/team/", "/services/", "/careers/", "/faq/", "/sitemap.xml", "/robots.txt"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_unknown_url_404(self):
        self.assertEqual(self.client.get("/nope/").status_code, 404)

    def test_nav_has_required_links(self):
        html = self.client.get("/").content.decode()
        for path in ["/team/", "/gallery/", "/contact-page/", "/about-us/", "/membership-procedure/"]:
            self.assertIn(f'href="{path}"', html)

    def test_admin_requires_login(self):
        self.assertEqual(self.client.get("/admin/").status_code, 302)


class TeamTests(Base):
    def test_unpublished_member_hidden_and_published_shown(self):
        m = TeamMember.objects.create(name="Temp Person", designation="Tester")
        self.assertNotIn("Temp Person", self.client.get("/team/").content.decode())
        m.is_published = True
        m.save()
        self.assertIn("Temp Person", self.client.get("/team/").content.decode())

    def test_former_member_separated(self):
        TeamMember.objects.create(name="Old Hand", designation="Ex", is_published=True, is_former=True)
        html = self.client.get("/team/").content.decode()
        self.assertIn("Former members", html)


class BranchTests(Base):
    def test_new_branch_appears_when_published(self):
        b = Branch.objects.create(name="Abia Branch", state="Kwara", city="Ilorin", phone="+234 800 000 0000, +234 800 000 0001")
        self.assertNotIn("Ilorin", self.client.get("/contact-page/").content.decode())
        b.is_published = True
        b.save()
        html = self.client.get("/contact-page/").content.decode()
        self.assertIn("Abia Branch", html)
        self.assertIn('href="tel:+2348000000000"', html)
        self.assertIn('href="tel:+2348000000001"', html)
        self.assertNotIn("Abia Branch", _re.sub(r"<script.*?</script>", "", self.client.get("/contact-page/?state=Lagos").content.decode(), flags=_re.S))  # JSON-LD lists all branches by design

    def test_duplicate_branch_rejected(self):
        Branch.objects.create(name="X", state="Edo")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Branch.objects.create(name="X", state="Edo")


class ContactFormTests(Base):
    data = {"name": "Ada", "email": "ada@example.com", "subject": "Hello", "message": "Hi there", "consent": "on"}

    def test_valid_submission_stored(self):
        r = self.client.post("/contact-page/", self.data)
        self.assertRedirects(r, "/contact-page/?sent=1", fetch_redirect_response=False)
        self.assertEqual(ContactSubmission.objects.count(), 1)

    def test_server_side_validation(self):
        r = self.client.post("/contact-page/", {**self.data, "email": "bad"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ContactSubmission.objects.count(), 0)

    def test_honeypot_blocks_bots(self):
        self.client.post("/contact-page/", {**self.data, "website": "http://spam"})
        self.assertEqual(ContactSubmission.objects.count(), 0)

    def test_rate_limit(self):
        for _ in range(7):
            self.client.post("/contact-page/", self.data)
        self.assertEqual(ContactSubmission.objects.count(), 5)

    def test_submissions_not_public(self):
        self.client.post("/contact-page/", self.data)
        self.assertNotIn("ada@example.com", self.client.get("/contact-page/").content.decode())


class HomeTests(Base):
    def test_homepage_shows_live_site_content(self):
        h = self.client.get("/").content.decode()
        for needle in ["12,000+", "46+", "2,930", "Years of experience", "46 years of experience", "Our proud", "Our core services",
                       "Recognized safety professional body in Nigeria", "Meet the team", "Latest media", "Past event", "Umuahia 2026"]:
            self.assertIn(needle, h, needle)
        self.assertIn('href="tel:+2348062083053"', h)  # top bar

    def test_hidden_statistic_is_not_shown(self):
        Statistic.objects.filter(label="Colleagues and counting").update(visible=False)
        HomePage.objects.get().save_revision().publish()
        h = self.client.get("/").content.decode()
        self.assertNotIn("2,930", h)
        self.assertIn("12,000+", h)

    def test_announcement_past_label(self):
        home = HomePage.objects.get()
        home.announcement_visible, home.announcement_title = True, "Conference"
        home.announcement_ends = datetime.date.today() - datetime.timedelta(days=3)
        home.save_revision().publish()
        self.assertIn("Past event", self.client.get("/").content.decode())


class GalleryTests(Base):
    def test_draft_album_hidden_live_album_shown(self):
        idx = GalleryIndexPage.objects.get()
        album = idx.add_child(instance=AlbumPage(title="Induction 2026", slug="induction-2026", live=False))
        self.assertNotIn("Induction 2026", self.client.get("/gallery/").content.decode())
        self.assertEqual(self.client.get("/gallery/induction-2026/").status_code, 404)
        album.live = True
        album.save()
        self.assertIn("Induction 2026", self.client.get("/gallery/").content.decode())
        self.assertEqual(self.client.get("/gallery/induction-2026/").status_code, 200)


class PermissionTests(Base):
    def user_in(self, group):
        u = get_user_model().objects.create_user(username=group.replace(" ", "").replace("&", ""), password="x" * 14)
        u.groups.add(Group.objects.get(name=group))
        self.client.force_login(u)

    def test_gallery_manager_boundaries(self):
        self.user_in("Gallery Manager")
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        self.assertNotEqual(self.client.get("/admin/users/").status_code, 200)
        home = Page.objects.get(slug="home")
        self.assertNotEqual(self.client.get(f"/admin/pages/{home.pk}/edit/").status_code, 200)
        gal = Page.objects.get(slug="gallery")
        self.assertEqual(self.client.get(f"/admin/pages/{gal.pk}/edit/").status_code, 200)

    def test_team_manager_cannot_manage_users(self):
        self.user_in("Branch & Team Manager")
        self.assertNotEqual(self.client.get("/admin/users/").status_code, 200)


class SeedContentTests(Base):
    def test_real_content_loaded(self):
        self.assertEqual(Branch.objects.count(), 17)
        self.assertEqual(TeamMember.objects.count(), 14)
        self.assertFalse(TeamMember.objects.filter(portrait=None).exists())
        self.assertFalse(BlogPostPage.objects.filter(featured_image=None).exists())
        self.assertEqual(TeamMember.objects.get(name__contains="Nwosu").unit, "Governing Board")
        self.assertEqual(TeamMember.objects.filter(is_published=True).count(), 14)
        html = self.client.get("/membership-procedure/").content.decode()
        self.assertIn("50,000", html)
        self.assertIn("Corporate membership procedure", html)
        self.assertIn("1978", self.client.get("/about-us/").content.decode())

    def test_all_branch_phones_normalised(self):
        for b in Branch.objects.exclude(phone=""):
            for n in b.phone.split(", "):
                self.assertRegex(n, r"^0\d{10}$")


class NewsTests(Base):
    def blog(self):
        from apps.news.models import BlogIndexPage
        return BlogIndexPage.objects.get()

    def test_listing_pagination_and_filters(self):
        r = self.client.get("/blog/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.get("/blog/?page=2").status_code, 200)
        self.assertIn("Anambra", self.client.get("/blog/?q=anambra").content.decode())
        self.assertIn("No articles match", self.client.get("/blog/?q=zzzzqqq").content.decode())
        self.assertEqual(self.client.get("/blog/?category=ispon-updates").status_code, 200)

    def test_article_page_and_jsonld(self):
        html = self.client.get("/blog/ispon-anambra-state-branch-is-a-goal/").content.decode()
        self.assertIn("NewsArticle", html)
        self.assertIn("Breadcrumb", html)
        self.assertNotIn("</script><script", html.split("application/ld+json")[1][:600])

    def test_old_dated_url_redirects_permanently(self):
        r = self.client.get("/2026/03/20/ispon-anambra-state-branch-is-a-goal/")
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r["Location"], "/blog/ispon-anambra-state-branch-is-a-goal/")

    def test_draft_and_scheduled_posts_hidden(self):
        from django.utils import timezone
        from apps.news.models import BlogPostPage
        draft = self.blog().add_child(instance=BlogPostPage(title="Secret", slug="secret", live=False))
        self.assertEqual(self.client.get("/blog/secret/").status_code, 404)
        self.assertNotIn("Secret", self.client.get("/blog/").content.decode())
        draft.go_live_at = timezone.now() + datetime.timedelta(days=2)
        draft.save_revision().publish()  # scheduled, not live yet
        self.assertEqual(self.client.get("/blog/secret/").status_code, 404)

    def test_homepage_shows_news(self):
        self.assertIn("Safety Vanguard", self.client.get("/").content.decode())

    def test_site_search_finds_articles_and_pages(self):
        self.assertIn("Anambra", self.client.get("/search/?q=Anambra").content.decode())
        self.assertIn("Membership", self.client.get("/search/?q=membership").content.decode())
        self.assertEqual(self.client.get("/search/?q=").status_code, 200)


class NewsletterTests(Base):
    def post(self, **kw):
        return self.client.post("/newsletter/subscribe/", {"email": "A@Example.com", "consent": "on", **kw})

    def sub(self):
        from apps.subscriptions.models import Subscriber
        return Subscriber.objects.get(email="a@example.com")

    def test_double_opt_in_flow(self):
        from django.core import mail
        self.assertContains(self.post(), "we have sent it a confirmation link")
        self.assertEqual(len(mail.outbox), 1)
        sub = self.sub()
        self.assertIsNone(sub.confirmed_at)
        self.assertIn(f"/newsletter/confirm/{sub.token}/", mail.outbox[0].body)
        self.client.get(f"/newsletter/confirm/{sub.token}/")  # opening the link (e.g. a mail scanner) must not confirm
        sub.refresh_from_db()
        self.assertIsNone(sub.confirmed_at)
        self.assertContains(self.client.post(f"/newsletter/confirm/{sub.token}/"), "confirmed")
        sub.refresh_from_db()
        self.assertIsNotNone(sub.confirmed_at)

    def test_no_enumeration_and_resend_throttle(self):
        from django.core import mail
        first = self.post().content
        second = self.post().content  # same address again within minutes
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(first.split(b"role=\"status\"")[1][:140], second.split(b"role=\"status\"")[1][:140])

    def test_send_failure_is_reported_honestly(self):
        from unittest import mock
        with mock.patch("apps.subscriptions.mail.EmailMultiAlternatives.send", side_effect=OSError("smtp down")):
            r = self.post()
        self.assertEqual(r.status_code, 503)
        self.assertContains(r, "could not send", status_code=503)
        self.assertNotIn("sent it a confirmation", r.content.decode())

    def test_unsubscribe_then_resubscribe_needs_new_confirmation(self):
        from django.utils import timezone
        self.post()
        sub = self.sub()
        sub.confirmed_at = timezone.now()
        sub.save()
        self.assertContains(self.client.get(f"/newsletter/unsubscribe/{sub.token}/"), "Confirm unsubscribe")
        sub.refresh_from_db()
        self.assertTrue(sub.is_active)  # GET alone never unsubscribes
        self.client.post(f"/newsletter/unsubscribe/{sub.token}/")
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)
        sub.confirmation_sent_at = None
        sub.save()
        self.post()
        sub.refresh_from_db()
        self.assertTrue(sub.is_active)
        self.assertIsNone(sub.confirmed_at)

    def test_one_click_unsubscribe_without_csrf(self):
        from django.test import Client
        self.post()
        sub = self.sub()
        r = Client(enforce_csrf_checks=True).post(f"/newsletter/one-click/{sub.token}/", {"List-Unsubscribe": "One-Click"})
        self.assertEqual(r.status_code, 200)
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)

    def test_validation_consent_honeypot_get(self):
        self.assertEqual(self.post(email="bad").status_code, 400)
        self.assertEqual(self.client.post("/newsletter/subscribe/", {"email": "x@y.com"}).status_code, 400)
        self.assertEqual(self.post(website="spam").status_code, 400)
        self.assertEqual(self.client.get("/newsletter/subscribe/").status_code, 405)


class NewsletterSendingTests(Base):
    def setUp(self):
        super().setUp()
        from django.utils import timezone
        from apps.subscriptions.models import Newsletter, Subscriber
        now = timezone.now()
        Subscriber.objects.create(email="ok1@example.com", confirmed_at=now)
        Subscriber.objects.create(email="ok2@example.com", confirmed_at=now)
        Subscriber.objects.create(email="unconfirmed@example.com")
        Subscriber.objects.create(email="gone@example.com", confirmed_at=now, is_active=False)
        self.nl = Newsletter.objects.create(subject="October update", body="<p>Hello <a href='https://ispon.gov.ng'>site</a></p>")

    def test_only_confirmed_active_subscribers_get_it_once_in_batches(self):
        from django.core import mail
        from django.core.management import call_command
        call_command("send_newsletters")
        self.assertEqual(len(mail.outbox), 0)  # draft is never sent
        self.nl.status = "queued"
        self.nl.save()
        call_command("send_newsletters", batch=1)
        self.assertEqual(len(mail.outbox), 1)
        self.nl.refresh_from_db()
        self.assertEqual(self.nl.status, "queued")
        call_command("send_newsletters", batch=10)
        call_command("send_newsletters", batch=10)  # re-run: no duplicates
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ["ok1@example.com", "ok2@example.com"])
        self.nl.refresh_from_db()
        self.assertEqual(self.nl.status, "sent")
        m = mail.outbox[0]
        self.assertIn("/newsletter/unsubscribe/", m.body)
        self.assertIn("/newsletter/one-click/", m.extra_headers["List-Unsubscribe"])
        self.assertEqual(m.extra_headers["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click")
        self.assertIn("Hello", m.alternatives[0][0])

    def test_failed_delivery_is_recorded_not_retried_forever(self):
        from unittest import mock
        from django.core.management import call_command
        self.nl.status = "queued"
        self.nl.save()
        with mock.patch("apps.subscriptions.mail.EmailMultiAlternatives.send", side_effect=OSError("boom")):
            call_command("send_newsletters")
        self.assertEqual(self.nl.deliveries.exclude(error="").count(), 2)
        self.nl.refresh_from_db()
        self.assertEqual(self.nl.status, "sent")

    def test_admin_page_queue_test_and_permissions(self):
        from django.core import mail
        u = get_user_model().objects.create_superuser("root", "root@example.com", "x" * 14)
        self.client.force_login(u)
        self.assertContains(self.client.get("/admin/newsletter/send/"), "October update")
        self.client.post("/admin/newsletter/send/", {"id": self.nl.pk, "action": "test"})
        self.assertEqual(mail.outbox[-1].to, ["root@example.com"])
        self.client.post("/admin/newsletter/send/", {"id": self.nl.pk, "action": "queue"})
        self.nl.refresh_from_db()
        self.assertEqual(self.nl.status, "queued")
        self.client.logout()
        v = get_user_model().objects.create_user("gm", password="x" * 14)
        v.groups.add(Group.objects.get(name="Gallery Manager"))
        self.client.force_login(v)
        self.assertNotEqual(self.client.get("/admin/newsletter/send/").status_code, 200)
        m = get_user_model().objects.create_user("nm", password="x" * 14)
        m.groups.add(Group.objects.get(name="Newsletter Manager"))
        self.client.force_login(m)
        self.assertEqual(self.client.get("/admin/newsletter/send/").status_code, 200)


class AccessibilityBasicsTests(Base):
    """Static checks only. Browser-based audits (axe, keyboard) are listed in README."""

    PAGES = ["/", "/blog/", "/blog/ispon-anambra-state-branch-is-a-goal/", "/about-us/", "/contact-page/", "/gallery/", "/membership-procedure/", "/team/", "/search/?q=x"]

    def test_basics(self):
        import re
        for url in self.PAGES:
            h = re.sub(r'<div class="hp".*?</div>', "", self.client.get(url).content.decode(), flags=re.S)  # honeypots are hidden decoys
            self.assertIn('<html lang="en-NG">', h, url)
            self.assertIn('class="skip"', h, url)
            self.assertEqual(len(re.findall(r"<h1[ >]", h)), 1, f"{url} should have exactly one h1")
            for img in re.findall(r"<img\b[^>]*>", h):
                self.assertIn("alt=", img, f"{url}: {img[:80]}")
            for inp in re.findall(r'<input\b[^>]*\bid="([^"]+)"', h):
                self.assertIn(f'for="{inp}"', h, f"{url}: input {inp} has no label")


import io
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image as PILImage

from apps.core.models import MembershipFee, MembershipPage
from apps.news.models import BlogPostPage


def png_bytes(color=(10, 107, 59)):
    buf = io.BytesIO()
    PILImage.new("RGB", (40, 30), color).save(buf, "PNG")
    return buf.getvalue()


class FeesTests(Base):
    def test_fees_render_and_are_editable(self):
        html = self.client.get("/membership-procedure/").content.decode()
        for amt in ("50,000", "15,000", "150,000", "100,000"):
            self.assertIn(amt, html)
        fee = MembershipFee.objects.get(label="Membership form")
        fee.amount = 60000
        fee.save()
        html = self.client.get("/membership-procedure/").content.decode()
        self.assertIn("60,000", html)
        self.assertNotIn("&#8358;50,000", html)
        fee.visible = False
        fee.save()
        self.assertNotIn("Membership form", self.client.get("/membership-procedure/").content.decode().split("<table")[1] if "<table" in self.client.get("/membership-procedure/").content.decode() else "")


class AdminPanelTests(Base):
    def setUp(self):
        super().setUp()
        self.client.force_login(get_user_model().objects.create_superuser("root", "r@example.com", "x" * 14))

    def test_admin_screens_load(self):
        mp, post = MembershipPage.objects.get(), BlogPostPage.objects.first()
        self.assertContains(self.client.get("/admin/"), "Quick actions")
        for url in [f"/admin/pages/{mp.pk}/edit/", f"/admin/pages/{post.pk}/edit/", "/admin/snippets/organisation/branch/",
                    "/admin/snippets/organisation/teammember/", "/admin/snippets/subscriptions/subscriber/",
                    reverse("news_articles:index"), reverse("photo_albums:index"), reverse("gallery_bulk_upload")]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_news_article_text_editable_in_cms(self):
        post = BlogPostPage.objects.get(slug="ispon-anambra-state-branch-is-a-goal")
        r = self.client.get(f"/admin/pages/{post.pk}/edit/")
        self.assertContains(r, "Awka")  # seeded body is loaded in the editor


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class BulkUploadTests(Base):
    def album(self, live=True):
        return GalleryIndexPage.objects.get().add_child(instance=AlbumPage(title="Induction", slug="induction", live=live))

    def login(self, group=None):
        u = get_user_model().objects.create_user("u" + str(group or "su"), password="x" * 14, is_superuser=group is None)
        if group:
            u.groups.add(Group.objects.get(name=group))
        self.client.force_login(u)

    def up(self, album, *files):
        return self.client.post(reverse("gallery_bulk_upload"), {"album": album.pk, "photos": list(files)})

    def test_upload_publishes_to_album_and_survives_edit(self):
        self.login("Gallery Manager")
        album = self.album()
        f = lambda n, c=(1, 2, 3): SimpleUploadedFile(n, png_bytes(c), "image/png")
        self.up(album, f("a.png"), f("dup.png"), f("b.png", (9, 9, 9)))  # dup.png is identical to a.png
        self.assertEqual(AlbumImage.objects.filter(page=album).count(), 2)
        self.assertEqual(album.get_latest_revision_as_object().images.count(), 2)  # editor still has them
        self.assertIn("<img", self.client.get("/gallery/induction/").content.decode())
        self.assertEqual(len(self.client.get("/gallery/").context["pins"]), 2)

    def test_rejects_fake_images(self):
        self.login()
        album = self.album()
        self.up(album, SimpleUploadedFile("x.png", b"not an image", "image/png"), SimpleUploadedFile("x.txt", b"hi", "text/plain"))
        self.assertEqual(AlbumImage.objects.filter(page=album).count(), 0)

    def test_permissions(self):
        album = self.album()
        self.login("Branch & Team Manager")  # may upload media, may not edit albums
        self.up(album, SimpleUploadedFile("a.png", png_bytes(), "image/png"))
        self.assertEqual(AlbumImage.objects.filter(page=album).count(), 0)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("gallery_bulk_upload")).status_code, 302)


class PinterestGalleryTests(Base):
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_pins_show_title_description_alt_and_filter(self):
        from wagtail.images.models import Image
        from django.core.files.base import ContentFile
        idx = GalleryIndexPage.objects.get()
        img = Image(title="x")
        img.file.save("x.png", ContentFile(png_bytes()), save=False)
        img.width, img.height = 40, 30
        img.save()
        a = AlbumPage(title="Conference", slug="conference", images=[
            AlbumImage(image=img, title="Opening session", description="Delegates arrive.", alt_text="Crowd in a hall"),
            AlbumImage(image=img, title="Hidden one", alt_text="x", is_published=False)])
        idx.add_child(instance=a)
        a.save_revision().publish()
        html = self.client.get("/gallery/").content.decode()
        self.assertIn("Opening session", html)
        self.assertIn("Delegates arrive.", html)
        self.assertIn('alt="Crowd in a hall"', html)
        self.assertNotIn("Hidden one", html)
        self.assertIn("Opening session", self.client.get("/gallery/?album=conference").content.decode())
        self.assertNotIn("Opening session", self.client.get("/gallery/?album=nothing").content.decode())
        self.assertIn("Delegates arrive.", self.client.get("/gallery/conference/").content.decode())


import json
import re as _re


def ld_blocks(html):
    return [json.loads(b) for b in _re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, _re.S)]


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SEOTests(Base):
    def make_image(self, title="logo"):
        from wagtail.images.models import Image
        from django.core.files.base import ContentFile
        img = Image(title=title)
        img.file.save(f"{title}.png", ContentFile(png_bytes()), save=False)
        img.width, img.height = 40, 30
        img.save()
        return img

    def set_logo(self, **extra):
        from wagtail.models import Site
        from apps.core.models import SiteSettings
        s = SiteSettings.for_site(Site.objects.get(is_default_site=True))
        s.logo = self.make_image("isponlogo")
        for k, v in extra.items():
            setattr(s, k, v)
        s.save()

    def test_head_basics_without_logo(self):
        h = self.client.get("/").content.decode()
        for needle in ['rel="canonical"', 'property="og:title"', 'name="twitter:card" content="summary_large_image"', 'name="geo.region" content="NG-ED"',
                       'name="geo.placename" content="Benin City"', 'rel="manifest"', 'type="application/rss+xml"', "index,follow,max-image-preview:large"]:
            self.assertIn(needle, h)
        self.assertNotIn("geo.position", h)  # never publish invented coordinates

    def test_geo_position_when_coordinates_entered(self):
        from decimal import Decimal
        self.set_logo(geo_latitude=Decimal("6.400000"), geo_longitude=Decimal("5.600000"))
        h = self.client.get("/").content.decode()
        self.assertIn('name="geo.position" content="6.400000;5.600000"', h)
        org = [n for n in ld_blocks(h)[0]["@graph"] if n["@type"] == "Organization"][0]
        self.assertEqual(org["geo"]["latitude"], 6.4)

    def test_logo_drives_favicon_footer_share_image_and_admin(self):
        self.set_logo()
        h = self.client.get("/").content.decode()
        self.assertRegex(h, r'rel="icon" href="[^"]*fill-32x32')
        self.assertIn("fill-180x180", h)
        faq = self.client.get("/faq/").content.decode()  # a page with no picture of its own falls back to the logo
        self.assertIn("max-600x600", _re.search(r'property="og:image" content="([^"]+)"', faq).group(1))
        self.assertIn("max-240x240", h.split("<footer")[1])
        m = self.client.get("/site.webmanifest").json()
        self.assertEqual({i["sizes"] for i in m["icons"]}, {"192x192", "512x512"})
        self.assertEqual(self.client.get("/favicon.ico").status_code, 302)
        self.client.force_login(get_user_model().objects.create_superuser("root", "r@example.com", "x" * 14))
        self.assertIn("max-160x160", self.client.get("/admin/").content.decode())
        self.client.logout()
        self.assertIn("max-160x160", self.client.get("/admin/login/").content.decode())

    def test_article_share_image_is_its_featured_image(self):
        post = BlogPostPage.objects.get(slug="ispon-anambra-state-branch-is-a-goal")
        post.featured_image = self.make_image("anambra-photo")
        post.save_revision().publish()
        self.set_logo()
        h = self.client.get("/blog/ispon-anambra-state-branch-is-a-goal/").content.decode()
        og = _re.search(r'property="og:image" content="([^"]+)"', h).group(1)
        self.assertIn("anambra-photo", og)
        self.assertIn("fill-1200x630", og)
        self.assertTrue(og.startswith("http"))
        self.assertIn('content="article"', h)
        self.assertIn("article:published_time", h)
        self.assertIn("summary_large_image", h)

    def test_json_ld_valid_everywhere(self):
        for url in ["/", "/blog/", "/blog/ispon-anambra-state-branch-is-a-goal/", "/about-us/", "/contact-page/", "/gallery/", "/membership-procedure/", "/team/", "/faq/", "/services/", "/careers/"]:
            blocks = ld_blocks(self.client.get(url).content.decode())
            self.assertEqual(len(blocks), 1, url)
            types = {n["@type"] for n in blocks[0]["@graph"]}
            self.assertTrue({"Organization", "WebSite"} <= types, url)
            if url != "/":
                self.assertIn("BreadcrumbList", types, url)
        art = [n for n in ld_blocks(self.client.get("/blog/ispon-anambra-state-branch-is-a-goal/").content.decode())[0]["@graph"] if n["@type"] == "NewsArticle"][0]
        self.assertEqual(art["datePublished"], "2026-03-20")
        contact = ld_blocks(self.client.get("/contact-page/").content.decode())[0]["@graph"]
        org = [n for n in contact if n["@type"] == "Organization"][0]
        self.assertEqual(len(org["subOrganization"]), 17)
        self.assertEqual(org["address"]["addressLocality"], "Benin City")

    def test_noindex_for_search_filters_and_newsletter(self):
        self.assertIn("noindex,follow", self.client.get("/search/?q=x").content.decode())
        self.assertIn("noindex,follow", self.client.get("/blog/?q=anambra").content.decode())
        self.assertIn("noindex,follow", self.client.post("/newsletter/subscribe/", {"email": "bad"}).content.decode())
        self.assertIn("index,follow", self.client.get("/blog/").content.decode())

    def test_robots_sitemap_and_feed(self):
        self.assertIn("Sitemap: http://testserver/sitemap.xml", self.client.get("/robots.txt").content.decode())
        sm = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("/blog/ispon-anambra-state-branch-is-a-goal/", sm)
        feed = self.client.get("/blog/feed/")
        self.assertEqual(feed.status_code, 200)
        self.assertIn("Anambra", feed.content.decode())


class HomepageAdminTests(Base):
    def test_homepage_menu_and_tabs(self):
        self.client.force_login(get_user_model().objects.create_superuser("root", "r@example.com", "x" * 14))
        r = self.client.get("/admin/homepage/")
        home = HomePage.objects.get()
        self.assertRedirects(r, f"/admin/pages/{home.pk}/edit/", fetch_redirect_response=False)
        page = self.client.get(f"/admin/pages/{home.pk}/edit/").content.decode()
        for tab in ["Hero and event", "About and highlights", "Our proud and numbers", "Services", "Team and news headings"]:
            self.assertIn(tab, page)
        self.assertIn('href="/admin/homepage/"', self.client.get("/admin/").content.decode())

    def test_content_administrator_can_edit_homepage_but_gallery_manager_cannot(self):
        home = HomePage.objects.get()
        for grp, ok in [("Content Administrator", True), ("Gallery Manager", False)]:
            u = get_user_model().objects.create_user(grp[:3] + "u", password="x" * 14)
            u.groups.add(Group.objects.get(name=grp))
            self.client.force_login(u)
            self.assertEqual(self.client.get(f"/admin/pages/{home.pk}/edit/").status_code == 200, ok, grp)


class OldSiteContentTests(Base):
    def test_team_page_matches_old_site(self):
        h = self.client.get("/team/").content.decode()
        for needle in ["Executive Member of ISPON Nigeria", "Dr. (Mrs.) Monica Nwosu", "Adm. (Mrs.) Joy Agbroko", "Need more information?", "mailto:president@ispon.gov.ng", "Registry"]:
            self.assertIn(needle, h)
        self.assertGreaterEqual(h.count('class="photo"'), 14)

    def test_register_button_and_social_links_in_header(self):
        h = self.client.get("/").content.decode()
        self.assertIn('class="navbtn" href="https://isponconf-2026.org/"', h)
        self.assertIn("https://x.com/isponng_safety", h.split('<footer class="ft">')[1])

    def test_about_page_sections(self):
        h = self.client.get("/about-us/").content.decode()
        for needle in ["Timeline", "Our experts", "Are you ready to take our service?", "Africa's largest organization", "1989"]:
            self.assertIn(needle.replace("'", "&#x27;") if needle not in h else needle, h)

    def test_blog_has_all_old_posts_with_pictures(self):
        h = self.client.get("/blog/?page=2").content.decode() + self.client.get("/blog/").content.decode()
        self.assertEqual(BlogPostPage.objects.count(), 12)
        self.assertEqual(self.client.get("/2026/05/12/membership-procedure/").status_code, 301)
        self.assertIn("<img", self.client.get("/blog/").content.decode())

    def test_footer_layout(self):
        f = self.client.get("/").content.decode().split('<footer class="ft">')[1]
        for needle in ["Stay informed", "Visit us", "Explore", "Contact", "Sitemap", "mailto:info@ispon.gov.ng"]:
            self.assertIn(needle, f)


class ImporterTests(Base):
    def test_importer_attaches_pictures_and_survives_failures(self):
        from unittest import mock
        from django.core.management import call_command
        from wagtail.models import Site
        from apps.core.models import SiteSettings
        calls = []

        def fake_fetch(url, timeout=25):
            calls.append(url)
            if "IMG-20260128-WA0004" in url:
                raise OSError("offline")
            return png_bytes((len(calls) % 250, 30, 60))
        with mock.patch("apps.core.management.commands.import_old_site_images.fetch", fake_fetch):
            call_command("import_old_site_images")
        self.assertIsNotNone(SiteSettings.for_site(Site.objects.get(is_default_site=True)).logo)
        self.assertIn("Udezi", TeamMember.objects.get(name__contains="Udezi").portrait.title)
        abia = BlogPostPage.objects.get(slug="abia-government-teams-up-with-ispon-to-enforce-safety-standards")
        self.assertEqual(abia.get_latest_revision_as_object().featured_image.title, "Abia Government Teams Up With ISPON To Enforce Safety Standards")
        album = AlbumPage.objects.get(slug="recent-work")
        self.assertEqual(AlbumImage.objects.filter(page=album).count(), 9)  # one of ten failed
        self.assertEqual(self.client.get("/gallery/recent-work/").status_code, 200)


class NewPagesTests(Base):
    def test_faq_has_schema_and_footer_links(self):
        h = self.client.get("/faq/").content.decode()
        self.assertIn("What is ISPON?", h)
        faq = [n for n in ld_blocks(h)[0]["@graph"] if n["@type"] == "FAQPage"][0]
        self.assertEqual(len(faq["mainEntity"]), 9)
        f = self.client.get("/").content.decode().split('<footer class="ft">')[1]
        for needle in ['href="/services/"', 'href="/careers/"', 'href="/faq/"']:
            self.assertIn(needle, f)
        self.assertNotIn('href="/faq/"', self.client.get("/").content.decode().split("</header>")[0])  # main menu stays at seven

    def test_hidden_faq_not_shown(self):
        from apps.core.models import FAQItem
        FAQItem.objects.filter(question__startswith="How can I stay").update(visible=False)
        self.assertNotIn("How can I stay updated?", self.client.get("/faq/").content.decode())

    def test_services_page_lists_home_cards(self):
        h = self.client.get("/services/").content.decode()
        for t in ["Consultancy", "Safety Conferences &amp; Workshops", "Professional Membership &amp; Certification"]:
            self.assertIn(t, h)

    def test_careers_empty_then_vacancy(self):
        from apps.core.models import CareerPage, Vacancy
        self.assertIn("No vacancies are listed", self.client.get("/careers/").content.decode())
        page = CareerPage.objects.get()
        Vacancy.objects.create(page=page, title="Programme Officer", location="Benin City", apply_email="hr@example.com", visible=True)
        Vacancy.objects.create(page=page, title="Hidden role", visible=False)
        h = self.client.get("/careers/").content.decode()
        self.assertIn("Programme Officer", h)
        self.assertIn("mailto:hr@example.com", h)
        self.assertNotIn("Hidden role", h)

    def test_about_is_designed_with_expert_portraits(self):
        h = self.client.get("/about-us/").content.decode()
        for needle in ['class="ab-hero"', 'class="tl"', "ab-facts", "Why choose us", "Dr. (Mrs.) Monica Nwosu", "Mr Benjamin Modebe"]:
            self.assertIn(needle, h)
        self.assertEqual(h.count('class="tcard"'), 4)
        self.assertEqual(h.count("<h1"), 1)

    def test_home_team_cards_have_pictures(self):
        h = self.client.get("/").content.decode()
        self.assertEqual(h.count('class="tcard"'), 4)
        self.assertIn("fill-400x480", h)

    def test_new_pages_editable_in_admin(self):
        self.client.force_login(get_user_model().objects.create_superuser("root", "r@example.com", "x" * 14))
        for slug in ["about-us", "services", "careers", "faq"]:
            pg = Page.objects.get(slug=slug)
            self.assertEqual(self.client.get(f"/admin/pages/{pg.pk}/edit/").status_code, 200, slug)


class HeroStyleTests(Base):
    PAGES = ["/blog/", "/blog/ispon-anambra-state-branch-is-a-goal/", "/contact-page/", "/gallery/", "/membership-procedure/", "/team/", "/services/", "/faq/", "/careers/", "/about-us/", "/search/?q=x"]

    def test_every_page_uses_the_dark_hero_band(self):
        for url in self.PAGES:
            h = self.client.get(url).content.decode()
            self.assertEqual(h.count('class="ab-hero"'), 1, url)
            self.assertEqual(h.count("<h1"), 1, url)

    def test_about_hero_has_image_on_the_right(self):
        h = self.client.get("/about-us/").content.decode()
        self.assertIn("ph-grid", h)
        self.assertIn('class="ph-img"', h)
        self.assertNotIn('class="ph-img"', self.client.get("/faq/").content.decode())

    def test_navbar_is_fixed_and_footer_has_social_links(self):
        h = self.client.get("/").content.decode()
        self.assertIn('<header class="top" id="navbar">', h)
        self.assertNotIn('class="topbar"', h)
        self.assertIn('class="soc"', h)



class UpgradeSiteTests(Base):
    """Simulate a database built before the new designs, then upgrade it."""

    def make_old(self):
        from wagtail.models import Page as WPage
        from apps.core.models import CareerPage, FAQPage, MembershipPage, ServicesPage, StandardPage
        home = HomePage.objects.get()
        for model in (AboutPage_, MembershipPage, ServicesPage, CareerPage, FAQPage):
            for pg in model.objects.all():
                pg.delete()
        for title, slug, menu in [("About Us", "about-us", True), ("Membership Procedure", "membership-procedure", True)]:
            pg = home.add_child(instance=StandardPage(title=title, slug=slug, show_in_menus=menu, intro="Old plain page"))
            pg.save_revision().publish()
        home.pillars.all().delete()
        HomePage.objects.get().save_revision().publish()

    def test_upgrade_converts_and_is_repeatable(self):
        from django.core.management import call_command
        from apps.core.models import StandardPage, Pillar
        self.make_old()
        self.assertNotIn('class="tl"', self.client.get("/about-us/").content.decode())  # plain page: no timeline
        call_command("upgrade_site")
        about = self.client.get("/about-us/").content.decode()
        self.assertIn('class="ab-hero"', about)
        self.assertIn('class="tl"', about)
        self.assertIn("Corporate membership procedure", self.client.get("/membership-procedure/").content.decode())
        self.assertIn("50,000", self.client.get("/membership-procedure/").content.decode())
        for url in ["/services/", "/careers/", "/faq/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        old = StandardPage.objects.get(slug="about-us-previous")
        self.assertFalse(old.live)
        self.assertEqual(self.client.get("/about-us-previous/").status_code, 404)
        self.assertTrue(Pillar.objects.exists())
        self.assertEqual(Page.objects.get(slug="about-us").get_next_sibling().pk, old.pk)  # takes the old page's place in the menu order
        counts = (Page.objects.count(), Pillar.objects.count())
        call_command("upgrade_site")  # second run changes nothing
        self.assertEqual((Page.objects.count(), Pillar.objects.count()), counts)


class HomepageRedesignTests(Base):
    def test_carousel_markup_and_controls(self):
        h = self.client.get("/").content.decode()
        self.assertEqual(h.count('class="hc-slide'), 3)
        self.assertIn('aria-roledescription="carousel"', h)
        for needle in ["hc-prev", "hc-next", "hc-pause", 'aria-label="Go to slide 3"', "hc-live"]:
            self.assertIn(needle, h)
        self.assertEqual(h.count("<h1"), 1)
        self.assertIn("flashlight", h)

    def test_numbers_are_count_up_ready(self):
        h = self.client.get("/").content.decode()
        self.assertIn('data-count="12000" data-prefix="" data-suffix="+">12,000+', h)  # final value is in the HTML (works without JavaScript)
        self.assertIn('data-count="46"', h)
        self.assertIn('data-count="2930"', h)

    def test_sections_are_in_a_sensible_order(self):
        h = self.client.get("/").content.decode()
        order = ['id="hero"', 'class="hm-band"', 'class="hm-about"', 'class="hm-why"', 'class="hm-svc"', 'class="tcards"', 'class="news"']
        pos = [h.index(x) for x in order]
        self.assertEqual(pos, sorted(pos))

    def test_about_has_image_and_story_link(self):
        h = self.client.get("/").content.decode()
        about = h.split('class="hm-about"')[1].split("</section>")[0]
        self.assertIn("<img", about)
        self.assertIn('href="/about-us/"', about)

    def test_video_slide_renders_and_validates(self):
        from django.core.exceptions import ValidationError
        from apps.core.models import HeroSlide
        home = HomePage.objects.get()
        v = HeroSlide(page=home, kind="video", headline="Watch\nus", video_url="https://example.com/clip.mp4", sort_order=9)
        v.full_clean()
        v.save()
        home.save_revision().publish()
        h = self.client.get("/").content.decode()
        self.assertIn('<source src="https://example.com/clip.mp4">', h)
        self.assertIn(" muted loop playsinline", h)
        for bad in (HeroSlide(page=home, kind="video", headline="x"), HeroSlide(page=home, kind="image", headline="x")):
            with self.assertRaises(ValidationError):
                bad.full_clean()

    def test_hidden_slide_and_fallback(self):
        from apps.core.models import HeroSlide
        HeroSlide.objects.filter(kind="image").update(visible=False)
        HomePage.objects.get().save_revision().publish()
        h = self.client.get("/").content.decode()
        self.assertEqual(h.count('class="hc-slide'), 1)
        self.assertNotIn("hc-prev", h)  # a single slide needs no controls
        HeroSlide.objects.all().delete()
        HomePage.objects.get().save_revision().publish()
        self.assertIn("See the", self.client.get("/").content.decode())  # simple hero fields take over

    def test_admin_home_editor_has_slides(self):
        self.client.force_login(get_user_model().objects.create_superuser("root", "r@example.com", "x" * 14))
        home = HomePage.objects.get()
        page = self.client.get(f"/admin/pages/{home.pk}/edit/").content.decode()
        self.assertIn("Hero slides", page)
        self.assertIn("hero_slides", page)
