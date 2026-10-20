"""News and blog: categories, tags, index page with filters and article pages."""
import datetime
import json

from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import TaggedItemBase
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageBlock
from wagtail.models import Page
from apps.core.models import SEOPage
from wagtail.search import index
from wagtail.snippets.models import register_snippet


@register_snippet
class BlogCategory(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    panels = [FieldPanel("name"), FieldPanel("slug")]

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "blog categories"

    def __str__(self):
        return self.name


class PostTag(TaggedItemBase):
    content_object = ParentalKey("news.BlogPostPage", related_name="tagged_items", on_delete=models.CASCADE)


class BlogIndexPage(SEOPage):
    max_count = 1
    parent_page_types = ["core.HomePage"]
    subpage_types = ["news.BlogPostPage"]
    intro = models.TextField(blank=True)
    content_panels = Page.content_panels + [FieldPanel("intro")]

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        all_posts = BlogPostPage.objects.child_of(self).live().select_related("featured_image", "category").order_by("-publication_date", "-pk")
        posts, cat, tag, q = all_posts, request.GET.get("category", ""), request.GET.get("tag", ""), request.GET.get("q", "").strip()[:100]
        if cat:
            posts = posts.filter(category__slug=cat)
        if tag:
            posts = posts.filter(tags__name=tag)
        if q:
            posts = posts.filter(Q(title__icontains=q) | Q(excerpt__icontains=q))
        filtered = bool(cat or tag or q)
        page_obj = Paginator(posts, 9).get_page(request.GET.get("page"))
        featured = None
        if not filtered and page_obj.number == 1:
            featured = all_posts.filter(is_featured=True).first()
        qs = "&".join(f"{k}={v}" for k, v in (("category", cat), ("tag", tag), ("q", q)) if v)
        ctx.update(posts=page_obj, featured=featured, categories=BlogCategory.objects.filter(blogpostpage__live=True).distinct(),
                   sel_cat=cat, sel_tag=tag, q=q, filtered=filtered, qs=qs)
        return ctx


class BlogPostPage(Page):
    parent_page_types = ["news.BlogIndexPage"]
    subpage_types = []
    publication_date = models.DateField(default=datetime.date.today)
    excerpt = models.TextField(max_length=320, blank=True)
    featured_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    body = StreamField(
        [
            ("heading", blocks.CharBlock(form_classname="title")),
            ("paragraph", blocks.RichTextBlock(features=["bold", "italic", "link", "ul", "ol", "h3", "blockquote"])),
            ("image", ImageBlock()),
            ("document", DocumentChooserBlock()),
        ],
        blank=True,
    )
    author_name = models.CharField("Author or editorial team", max_length=120, default="ISPON Editorial Team")
    category = models.ForeignKey(BlogCategory, null=True, blank=True, on_delete=models.SET_NULL)
    tags = ClusterTaggableManager(through=PostTag, blank=True)
    is_featured = models.BooleanField(default=False)
    social_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    canonical_url = models.URLField(blank=True)

    search_fields = Page.search_fields + [index.SearchField("excerpt"), index.SearchField("body"), index.FilterField("publication_date")]
    content_panels = Page.content_panels + [
        MultiFieldPanel([FieldPanel("publication_date"), FieldPanel("author_name"), FieldPanel("category"), FieldPanel("tags"), FieldPanel("is_featured")], "Details"),
        FieldPanel("excerpt"), FieldPanel("featured_image"), FieldPanel("body"),
    ]
    promote_panels = Page.promote_panels + [FieldPanel("social_image"), FieldPanel("canonical_url")]

    class Meta:
        indexes = [models.Index(fields=["publication_date"])]

    def related(self):
        qs = BlogPostPage.objects.live().exclude(pk=self.pk).select_related("featured_image").order_by("-publication_date")
        return (qs.filter(category=self.category) if self.category_id else qs)[:3]

    @property
    def json_ld(self):
        data = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": self.title, "datePublished": self.publication_date.isoformat(),
                "author": {"@type": "Organization", "name": self.author_name}, "mainEntityOfPage": self.full_url,
                "publisher": {"@type": "Organization", "name": "Institute of Safety Professionals of Nigeria"}}
        if self.search_description or self.excerpt:
            data["description"] = self.search_description or self.excerpt
        return json.dumps(data).replace("<", "\\u003c")
