"""Core page types: home page, generic content page and global site settings."""
from django.db import models
from django.utils import timezone
from modelcluster.fields import ParentalKey
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel, ObjectList, TabbedInterface
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.fields import RichTextField, StreamField
from wagtail.images.blocks import ImageBlock
from wagtail.models import Orderable, Page
from wagtail.search import index


class SEOPage(Page):
    """Base for public pages: adds a social sharing image (falls back to the site default or logo)."""

    social_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
                                     help_text="Picture shown when this page is shared. Recommended 1200x630.")
    show_in_footer = models.BooleanField(default=False, help_text="List this page in the website footer.")
    promote_panels = Page.promote_panels + [FieldPanel("social_image"), FieldPanel("show_in_footer")]

    class Meta:
        abstract = True


class HomePage(SEOPage):
    """Fully editable home page. Statistics and cards are hidden unless marked visible."""

    max_count = 1
    parent_page_types = ["wagtailcore.Page"]

    hero_headline = models.TextField(default="See the\nrisk\nfirst.", help_text="One line per row of the big headline.")
    hero_text = models.TextField(blank=True)
    cta_label = models.CharField("Main button label", max_length=40, blank=True)
    cta_url = models.CharField("Main button link", max_length=300, blank=True)
    cta2_label = models.CharField("Secondary button label", max_length=40, blank=True)
    cta2_url = models.CharField("Secondary button link", max_length=300, blank=True)

    intro_title = models.CharField(max_length=160, blank=True)
    intro_body = RichTextField(blank=True, features=["bold", "italic", "link", "ul", "ol"])
    intro_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    announcement_visible = models.BooleanField(default=False)
    announcement_title = models.CharField(max_length=200, blank=True)
    announcement_detail = models.CharField(max_length=300, blank=True)
    announcement_starts = models.DateField(null=True, blank=True)
    announcement_ends = models.DateField(null=True, blank=True)
    announcement_url = models.URLField(blank=True)
    announcement_button = models.CharField(max_length=40, blank=True)

    proud_kicker = models.CharField(max_length=60, blank=True, default="Our proud")
    proud_heading = models.CharField(max_length=120, blank=True, help_text="For example: 46 years of experience")
    proud_text = models.TextField(blank=True)
    services_title = models.CharField(max_length=80, blank=True, default="Our core services")
    services_intro = models.TextField(blank=True)
    team_title = models.CharField(max_length=80, blank=True, default="Meet the team")
    team_intro = models.TextField(blank=True)
    news_title = models.CharField(max_length=80, blank=True, default="Latest media")

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [FieldPanel("hero_headline"), FieldPanel("hero_text"), FieldPanel("cta_label"), FieldPanel("cta_url"),
             FieldPanel("cta2_label"), FieldPanel("cta2_url")],
            "Hero",
        ),
        MultiFieldPanel([FieldPanel("intro_title"), FieldPanel("intro_body"), FieldPanel("intro_image")], "Introduction"),
        MultiFieldPanel(
            [FieldPanel("announcement_visible"), FieldPanel("announcement_title"), FieldPanel("announcement_detail"),
             FieldPanel("announcement_starts"), FieldPanel("announcement_ends"), FieldPanel("announcement_url"),
             FieldPanel("announcement_button")],
            "Event or announcement banner",
        ),
        InlinePanel("services", label="Service cards"),
        InlinePanel("statistics", label="Statistics"),
    ]

    edit_handler = TabbedInterface([
        ObjectList(Page.content_panels + [
            MultiFieldPanel([FieldPanel("hero_headline"), FieldPanel("hero_text"), FieldPanel("cta_label"), FieldPanel("cta_url"),
                             FieldPanel("cta2_label"), FieldPanel("cta2_url")], "Hero (top of the page)"),
            MultiFieldPanel([FieldPanel("announcement_visible"), FieldPanel("announcement_title"), FieldPanel("announcement_detail"),
                             FieldPanel("announcement_starts"), FieldPanel("announcement_ends"), FieldPanel("announcement_url"),
                             FieldPanel("announcement_button")], "Upcoming event banner")], heading="Hero and event"),
        ObjectList([MultiFieldPanel([FieldPanel("intro_title"), FieldPanel("intro_body"), FieldPanel("intro_image")], "About ISPON"),
                    InlinePanel("pillars", label="Highlight")], heading="About and highlights"),
        ObjectList([FieldPanel("proud_kicker"), FieldPanel("proud_heading"), FieldPanel("proud_text"),
                    InlinePanel("statistics", label="Number")], heading="Our proud and numbers"),
        ObjectList([FieldPanel("services_title"), FieldPanel("services_intro"), InlinePanel("services", label="Service")], heading="Services"),
        ObjectList([FieldPanel("team_title"), FieldPanel("team_intro"), FieldPanel("news_title")], heading="Team and news headings"),
        ObjectList(SEOPage.promote_panels, heading="Promote"),
        ObjectList(Page.settings_panels, heading="Settings"),
    ])

    @property
    def headline_lines(self):
        return [ln for ln in self.hero_headline.splitlines() if ln.strip()]

    @property
    def announcement_is_past(self):
        end = self.announcement_ends or self.announcement_starts
        return bool(end and end < timezone.localdate())

    def get_context(self, request, *args, **kwargs):
        from apps.gallery.models import GalleryIndexPage
        from apps.news.models import BlogIndexPage, BlogPostPage
        from apps.organisation.models import TeamMember, TeamPage

        ctx = super().get_context(request, *args, **kwargs)
        ctx["services"] = [s for s in self.services.all() if s.visible]
        ctx["pillars"] = [x for x in self.pillars.all() if x.visible]
        ctx["stats"] = [s for s in self.statistics.all() if s.visible]
        ctx["blog_page"] = BlogIndexPage.objects.live().first()
        ctx["latest_news"] = BlogPostPage.objects.live().select_related("featured_image", "category").order_by("-is_featured", "-publication_date", "-pk")[:3]
        ctx["team_page"] = TeamPage.objects.live().first()
        ctx["gallery_page"] = GalleryIndexPage.objects.live().first()
        ctx["featured_team"] = TeamMember.objects.published().current().filter(featured=True).select_related("portrait")[:4]
        return ctx


class ServiceCard(Orderable):
    page = ParentalKey(HomePage, related_name="services", on_delete=models.CASCADE)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    link_url = models.CharField(max_length=300, blank=True)
    visible = models.BooleanField(default=True)
    panels = [FieldPanel("title"), FieldPanel("description"), FieldPanel("link_url"), FieldPanel("visible")]


class Pillar(Orderable):
    """A highlight shown in the scrolling band and the highlights grid on the homepage."""

    page = ParentalKey(HomePage, related_name="pillars", on_delete=models.CASCADE)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    visible = models.BooleanField(default=True)
    panels = [FieldPanel("title"), FieldPanel("description"), FieldPanel("visible")]


class Statistic(Orderable):
    """A figure is only shown when marked visible. Never defaults to a number."""

    page = ParentalKey(HomePage, related_name="statistics", on_delete=models.CASCADE)
    label = models.CharField(max_length=120)
    value = models.PositiveIntegerField()
    prefix = models.CharField(max_length=8, blank=True)
    suffix = models.CharField(max_length=8, blank=True)
    visible = models.BooleanField(default=False, help_text="Tick only once the figure is verified.")
    panels = [FieldPanel("label"), FieldPanel("value"), FieldPanel("prefix"), FieldPanel("suffix"), FieldPanel("visible")]


def body_blocks():
    """Controlled set of content blocks shared by editable text pages."""
    return [
        ("heading", blocks.CharBlock(form_classname="title")),
        ("paragraph", blocks.RichTextBlock(features=["bold", "italic", "link", "ul", "ol", "h3"])),
        ("image", ImageBlock()),
        ("cta", blocks.StructBlock([("label", blocks.CharBlock()), ("url", blocks.URLBlock())])),
        ("document", DocumentChooserBlock()),
        (
            "faq",
            blocks.ListBlock(
                blocks.StructBlock([("question", blocks.CharBlock()), ("answer", blocks.RichTextBlock(features=["bold", "link"]))])
            ),
        ),
    ]


class StandardPage(SEOPage):
    """Reusable content page (About, etc.) built from controlled blocks."""

    intro = models.TextField(blank=True)
    body = StreamField(body_blocks(), blank=True)
    search_fields = Page.search_fields + [index.SearchField("intro"), index.SearchField("body")]
    content_panels = Page.content_panels + [FieldPanel("intro"), FieldPanel("body")]


class MembershipPage(SEOPage):
    """Membership procedure text plus a structured, editable fee schedule."""

    max_count = 1
    parent_page_types = ["core.HomePage"]
    intro = models.TextField(blank=True)
    body = StreamField(body_blocks(), blank=True)
    fees_note = models.CharField(max_length=300, blank=True, help_text="Shown under the fee tables.")
    fees_updated = models.DateField(null=True, blank=True, help_text="Date the fees were last confirmed.")

    search_fields = Page.search_fields + [index.SearchField("intro"), index.SearchField("body")]
    content_panels = Page.content_panels + [
        FieldPanel("intro"), FieldPanel("body"),
        MultiFieldPanel([InlinePanel("fees", label="Fee"), FieldPanel("fees_note"), FieldPanel("fees_updated")], "Fees"),
    ]

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        fees = [f for f in self.fees.all() if f.visible]
        ctx["individual_fees"] = [f for f in fees if f.audience == "individual"]
        ctx["corporate_fees"] = [f for f in fees if f.audience == "corporate"]
        return ctx


class MembershipFee(Orderable):
    AUDIENCES = [("individual", "Individual membership"), ("corporate", "Corporate membership")]
    page = ParentalKey(MembershipPage, related_name="fees", on_delete=models.CASCADE)
    audience = models.CharField(max_length=12, choices=AUDIENCES)
    label = models.CharField(max_length=160)
    amount = models.PositiveIntegerField(help_text="Amount in naira, digits only.")
    note = models.CharField(max_length=160, blank=True, help_text="For example: non-refundable.")
    visible = models.BooleanField(default=True)
    panels = [FieldPanel("audience"), FieldPanel("label"), FieldPanel("amount"), FieldPanel("note"), FieldPanel("visible")]


class AboutPage(SEOPage):
    """Designed About page: lead text, history, key facts, timeline, reasons, experts and a closing call to action."""

    max_count = 1
    parent_page_types = ["core.HomePage"]
    hero_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+", help_text="Picture on the right of the top band (desktop). Recommended 760 x 600.")
    lead = models.TextField(help_text="Large opening statement.")
    body = RichTextField(blank=True, features=["bold", "italic", "link", "ul", "ol"], help_text="History and background.")
    timeline_title = models.CharField(max_length=60, blank=True, default="Timeline")
    reasons_title = models.CharField(max_length=60, blank=True, default="Why choose us")
    experts_title = models.CharField(max_length=60, blank=True, default="Our experts")
    experts_text = models.CharField(max_length=240, blank=True)
    cta_title = models.CharField(max_length=120, blank=True)
    cta_text = models.CharField(max_length=240, blank=True)
    cta_label = models.CharField(max_length=40, blank=True)
    cta_url = models.CharField(max_length=300, blank=True)
    search_fields = Page.search_fields + [index.SearchField("lead"), index.SearchField("body")]
    content_panels = Page.content_panels + [
        FieldPanel("hero_image"), FieldPanel("lead"), FieldPanel("body"),
        InlinePanel("facts", label="Key fact"),
        MultiFieldPanel([FieldPanel("timeline_title"), InlinePanel("timeline", label="Timeline entry")], "Timeline"),
        MultiFieldPanel([FieldPanel("reasons_title"), InlinePanel("reasons", label="Reason")], "Why choose us"),
        MultiFieldPanel([FieldPanel("experts_title"), FieldPanel("experts_text"), InlinePanel("experts", label="Expert")], "Experts (pick from Team members)"),
        MultiFieldPanel([FieldPanel("cta_title"), FieldPanel("cta_text"), FieldPanel("cta_label"), FieldPanel("cta_url")], "Closing call to action"),
    ]


class AboutFact(Orderable):
    page = ParentalKey(AboutPage, related_name="facts", on_delete=models.CASCADE)
    value = models.CharField(max_length=30)
    label = models.CharField(max_length=140)
    panels = [FieldPanel("value"), FieldPanel("label")]


class TimelineEntry(Orderable):
    page = ParentalKey(AboutPage, related_name="timeline", on_delete=models.CASCADE)
    year = models.CharField(max_length=10)
    title = models.CharField(max_length=120)
    text = models.TextField(blank=True)
    panels = [FieldPanel("year"), FieldPanel("title"), FieldPanel("text")]


class AboutReason(Orderable):
    page = ParentalKey(AboutPage, related_name="reasons", on_delete=models.CASCADE)
    title = models.CharField(max_length=120)
    text = models.TextField()
    panels = [FieldPanel("title"), FieldPanel("text")]


class AboutExpert(Orderable):
    page = ParentalKey(AboutPage, related_name="experts", on_delete=models.CASCADE)
    member = models.ForeignKey("organisation.TeamMember", on_delete=models.CASCADE, related_name="+")
    panels = [FieldPanel("member")]


class ServicesPage(SEOPage):
    """Lists the service cards managed on the Home page, plus intro text and calls to action."""

    max_count = 1
    parent_page_types = ["core.HomePage"]
    intro = models.TextField(blank=True)
    body = StreamField(body_blocks(), blank=True)
    cta_label = models.CharField(max_length=40, blank=True)
    cta_url = models.CharField(max_length=300, blank=True)
    search_fields = Page.search_fields + [index.SearchField("intro"), index.SearchField("body")]
    content_panels = Page.content_panels + [FieldPanel("intro"), FieldPanel("body"), FieldPanel("cta_label"), FieldPanel("cta_url")]

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        home = HomePage.objects.first()
        ctx["services"] = [x for x in home.services.all() if x.visible] if home else []
        return ctx


class FAQPage(SEOPage):
    max_count = 1
    parent_page_types = ["core.HomePage"]
    intro = models.TextField(blank=True)
    search_fields = Page.search_fields + [index.SearchField("intro")]
    content_panels = Page.content_panels + [FieldPanel("intro"), InlinePanel("items", label="Question")]


class FAQItem(Orderable):
    page = ParentalKey(FAQPage, related_name="items", on_delete=models.CASCADE)
    question = models.CharField(max_length=240)
    answer = RichTextField(features=["bold", "italic", "link", "ul", "ol"])
    visible = models.BooleanField(default=True)
    panels = [FieldPanel("question"), FieldPanel("answer"), FieldPanel("visible")]


class CareerPage(SEOPage):
    max_count = 1
    parent_page_types = ["core.HomePage"]
    intro = RichTextField(blank=True, features=["bold", "italic", "link"])
    empty_text = models.CharField(max_length=240, blank=True, help_text="Shown when no vacancies are visible.")
    content_panels = Page.content_panels + [FieldPanel("intro"), FieldPanel("empty_text"), InlinePanel("vacancies", label="Vacancy")]

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        ctx["openings"] = [v for v in self.vacancies.all() if v.visible]
        return ctx


class Vacancy(Orderable):
    page = ParentalKey(CareerPage, related_name="vacancies", on_delete=models.CASCADE)
    title = models.CharField(max_length=160)
    location = models.CharField(max_length=120, blank=True)
    job_type = models.CharField("Type", max_length=60, blank=True, help_text="For example Full time")
    description = RichTextField(blank=True, features=["bold", "italic", "link", "ul", "ol"])
    apply_email = models.EmailField(blank=True)
    apply_url = models.URLField(blank=True)
    closing_date = models.DateField(null=True, blank=True)
    visible = models.BooleanField(default=True)
    panels = [FieldPanel("title"), FieldPanel("location"), FieldPanel("job_type"), FieldPanel("description"), FieldPanel("apply_email"),
              FieldPanel("apply_url"), FieldPanel("closing_date"), FieldPanel("visible")]


@register_setting(icon="cog")
class SiteSettings(BaseSiteSetting):
    logo = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    footer_text = models.TextField(blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    office_hours = models.CharField(max_length=160, blank=True)
    map_url = models.URLField("Approved map link", blank=True)
    facebook = models.URLField(blank=True)
    x_twitter = models.URLField("X (Twitter)", blank=True)
    instagram = models.URLField(blank=True)
    newsletter_text = models.CharField(max_length=200, blank=True)
    header_button_label = models.CharField(max_length=30, blank=True, help_text="Button at the end of the menu, for example Register Now. Needs a link too.")
    header_button_url = models.CharField(max_length=300, blank=True)
    default_description = models.TextField(blank=True, help_text="Used when a page has no description of its own (about 155 characters).")
    default_share_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
                                            help_text="Fallback picture for shared links (1200x630). The logo is used if empty.")
    twitter_handle = models.CharField("X (Twitter) handle", max_length=40, blank=True, help_text="For example @isponng_safety")
    google_verification = models.CharField("Google Search Console token", max_length=120, blank=True)
    bing_verification = models.CharField("Bing Webmaster token", max_length=120, blank=True)
    theme_color = models.CharField(max_length=7, default="#0a6b3b")
    address_region = models.CharField("State", max_length=80, default="Edo State")
    geo_placename = models.CharField("City", max_length=80, default="Benin City")
    geo_region = models.CharField("ISO region code", max_length=10, default="NG-ED", help_text="Nigeria state code, for example NG-ED, NG-LA, NG-FC")
    geo_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    geo_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    panels = [
        FieldPanel("logo"),
        FieldPanel("footer_text"), FieldPanel("newsletter_text"),
        MultiFieldPanel([FieldPanel("header_button_label"), FieldPanel("header_button_url")], "Menu button"),
        MultiFieldPanel([FieldPanel("address"), FieldPanel("phone"), FieldPanel("email"), FieldPanel("office_hours"), FieldPanel("map_url")], "Headquarters"),
        MultiFieldPanel([FieldPanel("facebook"), FieldPanel("x_twitter"), FieldPanel("instagram"), FieldPanel("twitter_handle")], "Social media"),
        MultiFieldPanel([FieldPanel("default_description"), FieldPanel("default_share_image"), FieldPanel("google_verification"),
                         FieldPanel("bing_verification"), FieldPanel("theme_color")], "Search and sharing"),
        MultiFieldPanel([FieldPanel("address_region"), FieldPanel("geo_placename"), FieldPanel("geo_region"),
                         FieldPanel("geo_latitude"), FieldPanel("geo_longitude")], "Location (geo tags)"),
    ]
