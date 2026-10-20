"""DEVELOPMENT ONLY: create sample albums with generated placeholder photos so the gallery can be previewed.
Never run this on the production site."""
import datetime
import io
import random

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image as PILImage, ImageDraw, ImageFont
from wagtail.images.models import Image

from apps.gallery.models import AlbumImage, AlbumPage, GalleryIndexPage

ALBUMS = [("Conferences", "Annual conference sessions", "Benin City"), ("Training programmes", "Hands-on safety training", "Lagos"),
          ("Professional inductions", "New member inductions", "Awka"), ("Awareness campaigns", "Safety awareness outreach", "Umuahia")]
SIZES = [(600, 800), (800, 600), (600, 600), (600, 900), (800, 520), (600, 740)]
COLORS = [(10, 107, 59), (255, 194, 14), (14, 18, 16), (60, 90, 70), (200, 150, 20)]


def fake_photo(n, size, rnd):
    w, h = size
    base = rnd.choice(COLORS)
    im = PILImage.new("RGB", size, base)
    d = ImageDraw.Draw(im)
    for x in range(-h, w, 44):
        d.polygon([(x, h), (x + 22, h), (x + 22 + h, 0), (x + h, 0)], fill=tuple(min(255, c + 28) for c in base))
    d.rectangle([w // 8, h // 3, w - w // 8, h - h // 4], outline=(241, 238, 230), width=6)
    d.text((w // 8 + 20, h // 3 + 20), f"SAMPLE {n:02d}", fill=(241, 238, 230), font=ImageFont.load_default(size=max(28, w // 10)))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82)
    return buf.getvalue()


class Command(BaseCommand):
    def handle(self, *a, **o):
        rnd, n, idx = random.Random(4), 0, GalleryIndexPage.objects.get()
        for ai, (title, desc, loc) in enumerate(ALBUMS):
            items = []
            for _ in range(7):
                n += 1
                size = rnd.choice(SIZES)
                img = Image(title=f"Sample photo {n}")
                img.file.save(f"sample{n}.jpg", ContentFile(fake_photo(n, size, rnd)), save=False)
                img.width, img.height = size
                img.save()
                items.append(AlbumImage(image=img, title=f"Sample photo {n}", alt_text=f"Placeholder image number {n}",
                                        description="A short optional description appears here." if n % 3 == 0 else "", sort_order=n))
            page = AlbumPage(title=title, slug=title.lower().replace(" ", "-"), description=f"<p>{desc}.</p>", location=loc,
                             event_date=datetime.date(2026, 3 + ai, 10), category=title, images=items)
            idx.add_child(instance=page)
            page.save_revision().publish()
        self.stdout.write("Demo gallery created (placeholder images, development only).")
