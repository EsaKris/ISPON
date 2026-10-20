"""Gallery: an index page, album pages and ordered album images."""
from django.core.paginator import Paginator
from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Orderable, Page

from apps.core.models import SEOPage


class AlbumPage(SEOPage):
    parent_page_types = ["gallery.GalleryIndexPage"]
    subpage_types = []
    description = RichTextField(blank=True, features=["bold", "italic", "link"])
    cover = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    event_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=160, blank=True)
    category = models.CharField(max_length=80, blank=True)
    featured = models.BooleanField(default=False)

    content_panels = Page.content_panels + [
        FieldPanel("description"), FieldPanel("cover"),
        MultiFieldPanel([FieldPanel("event_date"), FieldPanel("location"), FieldPanel("category"), FieldPanel("featured")], "Details"),
        InlinePanel("images", label="Images"),
    ]

    def published_images(self):
        return [i for i in self.images.all() if i.is_published]


class AlbumImage(Orderable):
    page = ParentalKey(AlbumPage, related_name="images", on_delete=models.CASCADE)
    image = models.ForeignKey("wagtailimages.Image", on_delete=models.CASCADE, related_name="+")
    title = models.CharField(max_length=120)
    description = models.TextField(max_length=300, blank=True, help_text="Optional short description shown under the photo.")
    alt_text = models.CharField(max_length=240, help_text="Describe the photo for people who cannot see it.")
    credit = models.CharField(max_length=120, blank=True)
    is_published = models.BooleanField(default=True)
    panels = [FieldPanel("image"), FieldPanel("title"), FieldPanel("description"), FieldPanel("alt_text"), FieldPanel("credit"), FieldPanel("is_published")]


class GalleryIndexPage(SEOPage):
    max_count = 1
    parent_page_types = ["core.HomePage"]
    subpage_types = ["gallery.AlbumPage"]
    intro = models.TextField(blank=True)
    content_panels = Page.content_panels + [FieldPanel("intro")]

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        albums = AlbumPage.objects.child_of(self).live().order_by("-event_date", "title")
        sel = request.GET.get("album", "")
        pins = (AlbumImage.objects.filter(page__in=albums, is_published=True).select_related("image", "page")
                .order_by("-page__event_date", "page__title", "sort_order"))
        if sel:
            pins = pins.filter(page__slug=sel)
        ctx.update(albums=albums, sel_album=sel, pins=Paginator(pins, 24).get_page(request.GET.get("page")))
        return ctx
