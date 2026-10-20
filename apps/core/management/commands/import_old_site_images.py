"""Download the pictures from the old ispon.gov.ng site into the CMS (logo, team portraits, news pictures, gallery photos).

Run this once on a machine with internet access (your computer or the cPanel terminal), only for pictures ISPON owns or has permission to use.
It replaces the generated starter artwork. Safe to re-run: identical files are reused.
"""
import hashlib
import io
import urllib.request

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image as PILImage
from wagtail.images.models import Image
from wagtail.models import Site

from apps.core.models import SiteSettings
from apps.core.seed_data import GALLERY_PHOTOS, LOGO_URL, OLD, POSTS, TEAM
from apps.gallery.models import AlbumImage, AlbumPage, GalleryIndexPage
from apps.news.models import BlogPostPage
from apps.organisation.models import TeamMember

MAX_BYTES = 12 * 1024 * 1024


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "ISPON-site-importer/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(MAX_BYTES)


def to_image(data, title, filename):
    """Validate with Pillow (never trust the URL) and store, reusing identical files."""
    with PILImage.open(io.BytesIO(data)) as im:
        if im.format not in {"JPEG", "PNG", "WEBP", "GIF"}:
            raise ValueError("unsupported image format")
        size = im.size
        im.verify()
    digest = hashlib.sha1(data).hexdigest()
    existing = Image.objects.filter(file_hash=digest).first()
    if existing:
        return existing
    img = Image(title=title[:255], file_hash=digest, file_size=len(data))
    img.file.save(filename.rsplit("/", 1)[-1][:80], ContentFile(data), save=False)
    img.width, img.height = size
    img.save()
    return img


class Command(BaseCommand):
    help = "Import pictures from the old ispon.gov.ng site."

    def add_arguments(self, parser):
        parser.add_argument("--only", default="logo,team,blog,gallery", help="Comma list of: logo, team, blog, gallery")

    def get(self, url, title):
        try:
            return to_image(fetch(url), title, url)
        except Exception as e:
            self.failed.append(f"{url}: {e}")
            return None

    def handle(self, *args, **o):
        only, self.failed, done = set(o["only"].split(",")), [], 0
        if "logo" in only:
            img = self.get(LOGO_URL, "ISPON logo")
            if img:
                s = SiteSettings.for_site(Site.objects.get(is_default_site=True))
                s.logo = img
                s.save()
                done += 1
        if "team" in only:
            for name, _d, _u, path in TEAM:
                m, img = TeamMember.objects.filter(name=name).first(), None
                if m and (img := self.get(OLD + path, f"{name} portrait")):
                    m.portrait = img
                    m.save()
                    done += 1
        if "blog" in only:
            for _date, slug, title, _exc, path in POSTS:
                page = BlogPostPage.objects.filter(slug=slug).first()
                if page and path and (img := self.get(OLD + path, title)):
                    page.featured_image = img
                    page.save_revision().publish()
                    done += 1
        if "gallery" in only:
            idx = GalleryIndexPage.objects.first()
            if idx:
                album = AlbumPage.objects.filter(slug="recent-work").first()
                if not album:
                    album = idx.add_child(instance=AlbumPage(title="Recent work", slug="recent-work", description="<p>Our recent work.</p>"))
                    album.save_revision().publish()
                obj = album.get_latest_revision_as_object()
                have = {ai.image_id for ai in obj.images.all()}
                added = 0
                for n, url in enumerate(GALLERY_PHOTOS, 1):
                    img = self.get(url, f"Recent work {n}")
                    if img and img.pk not in have:
                        obj.images.add(AlbumImage(image=img, title=f"Recent work {n}", alt_text="Photo from an ISPON event", sort_order=len(have)))
                        have.add(img.pk)
                        added += 1
                if added:
                    rev = obj.save_revision()
                    if album.live:
                        rev.publish()
                    done += added
        self.stdout.write(f"Imported {done} picture(s).")
        for f in self.failed:
            self.stdout.write(self.style.WARNING("Could not import " + f))
