"""Team members, branches and the contact page."""
from django import forms
from django.core.cache import cache
from django.db import models
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from apps.core.models import SEOPage

STATES = [
    (s, s)
    for s in (
        "Abia|Adamawa|Akwa Ibom|Anambra|Bauchi|Bayelsa|Benue|Borno|Cross River|Delta|Ebonyi|Edo|Ekiti|Enugu|"
        "FCT Abuja|Gombe|Imo|Jigawa|Kaduna|Kano|Katsina|Kebbi|Kogi|Kwara|Lagos|Nasarawa|Niger|Ogun|Ondo|Osun|"
        "Oyo|Plateau|Rivers|Sokoto|Taraba|Yobe|Zamfara"
    ).split("|")
]


class TeamQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)

    def current(self):
        return self.filter(is_former=False)


class TeamMember(models.Model):
    name = models.CharField(max_length=160)
    designation = models.CharField(max_length=160)
    unit = models.CharField("Department or unit", max_length=120, blank=True)
    bio = RichTextField(blank=True, features=["bold", "italic", "link"])
    portrait = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    email = models.EmailField(blank=True)
    term_start = models.DateField(null=True, blank=True)
    term_end = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first.")
    is_published = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    is_former = models.BooleanField("Former member (archive)", default=False)

    objects = TeamQuerySet.as_manager()

    panels = [
        FieldPanel("name"), FieldPanel("designation"), FieldPanel("unit"), FieldPanel("portrait"), FieldPanel("bio"),
        FieldPanel("email"), FieldPanel("term_start"), FieldPanel("term_end"),
        MultiFieldPanel([FieldPanel("order"), FieldPanel("is_published"), FieldPanel("featured"), FieldPanel("is_former")], "Display"),
    ]

    class Meta:
        ordering = ["order", "name"]
        indexes = [models.Index(fields=["is_published", "is_former", "order"])]

    def __str__(self):
        return f"{self.name} ({self.designation})"


class Branch(models.Model):
    name = models.CharField("Branch name", max_length=160)
    state = models.CharField(max_length=40, choices=STATES)
    city = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    contact_person = models.CharField("Chairman or contact person", max_length=160, blank=True)
    phone = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True)
    map_url = models.URLField("Approved map link", blank=True)
    image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)

    panels = [
        FieldPanel("name"), FieldPanel("state"), FieldPanel("city"), FieldPanel("address"), FieldPanel("contact_person"),
        FieldPanel("phone"), FieldPanel("email"), FieldPanel("map_url"), FieldPanel("image"),
        MultiFieldPanel([FieldPanel("order"), FieldPanel("is_published"), FieldPanel("featured")], "Display"),
    ]

    class Meta:
        ordering = ["state", "order", "name"]
        constraints = [models.UniqueConstraint(fields=["name", "state"], name="uniq_branch_name_state")]
        indexes = [models.Index(fields=["is_published", "state"])]
        verbose_name_plural = "branches"

    def __str__(self):
        return f"{self.name}, {self.state}"


class ContactSubmission(models.Model):
    """Stored messages. Visible only to staff granted permission on this model."""

    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=160)
    message = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    panels = [FieldPanel("name"), FieldPanel("email"), FieldPanel("subject"), FieldPanel("message"), FieldPanel("is_read")]

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} from {self.name}"


class ContactForm(forms.ModelForm):
    consent = forms.BooleanField(required=True, error_messages={"required": "Please confirm you have read the Privacy Policy."})
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))  # honeypot

    class Meta:
        model = ContactSubmission
        fields = ["name", "email", "subject", "message"]

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return ""


class TeamPage(SEOPage):
    max_count = 1
    parent_page_types = ["core.HomePage"]
    heading = models.CharField(max_length=120, blank=True, help_text="Line above the page title, for example Executive Member of ISPON Nigeria.")
    intro = models.TextField(blank=True)
    cta_title = models.CharField("Contact box title", max_length=80, blank=True)
    cta_email = models.EmailField("Contact box email", blank=True)
    content_panels = Page.content_panels + [FieldPanel("heading"), FieldPanel("intro"), FieldPanel("cta_title"), FieldPanel("cta_email")]

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        qs = TeamMember.objects.published().select_related("portrait")
        ctx["members"] = qs.current()
        ctx["former"] = qs.filter(is_former=True)
        return ctx


class ContactPage(SEOPage):
    max_count = 1
    parent_page_types = ["core.HomePage"]
    intro = RichTextField(blank=True, features=["bold", "link"])
    content_panels = Page.content_panels + [FieldPanel("intro")]

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        branches = Branch.objects.filter(is_published=True)
        state, q = request.GET.get("state", ""), request.GET.get("q", "").strip()
        if state:
            branches = branches.filter(state=state)
        if q:
            branches = branches.filter(models.Q(name__icontains=q) | models.Q(city__icontains=q))
        ctx.update(
            branches=branches,
            states=Branch.objects.filter(is_published=True).order_by("state").values_list("state", flat=True).distinct(),
            sel_state=state, q=q, sent=request.GET.get("sent") == "1",
        )
        ctx.setdefault("form", ContactForm())
        return ctx

    def serve(self, request, *args, **kwargs):
        if request.method != "POST":
            return super().serve(request, *args, **kwargs)
        form = ContactForm(request.POST)
        key = f"contact:{request.META.get('REMOTE_ADDR', '')}"
        sent_count = cache.get(key, 0)
        if sent_count >= 5:
            form.add_error(None, "Too many messages from this connection. Please try again later.")
        elif form.is_valid():
            form.save()
            cache.set(key, sent_count + 1, 3600)
            return redirect(self.url + "?sent=1")
        ctx = self.get_context(request)
        ctx["form"] = form
        return TemplateResponse(request, self.get_template(request), ctx)
