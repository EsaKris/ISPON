import uuid

from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField


class Subscriber(models.Model):
    """Newsletter subscriber (double opt-in). Only confirmed, active subscribers receive newsletters."""

    email = models.EmailField(unique=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    consented_at = models.DateTimeField(auto_now_add=True)
    confirmation_sent_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    panels = [FieldPanel("email"), FieldPanel("is_active")]

    class Meta:
        ordering = ["-consented_at"]

    def __str__(self):
        return self.email


class Newsletter(models.Model):
    DRAFT, QUEUED, SENT = "draft", "queued", "sent"
    STATUS = [(DRAFT, "Draft"), (QUEUED, "Queued / sending"), (SENT, "Sent")]
    subject = models.CharField(max_length=150)
    body = RichTextField(features=["bold", "italic", "link", "ul", "ol", "h3"])
    status = models.CharField(max_length=8, choices=STATUS, default=DRAFT, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    queued_at = models.DateTimeField(null=True, blank=True, editable=False)
    sent_at = models.DateTimeField(null=True, blank=True, editable=False)
    panels = [FieldPanel("subject"), FieldPanel("body")]

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.subject

    def recipients(self):
        return Subscriber.objects.filter(is_active=True, confirmed_at__isnull=False)

    def pending(self):
        return self.recipients().exclude(deliveries__newsletter=self)


class NewsletterDelivery(models.Model):
    newsletter = models.ForeignKey(Newsletter, on_delete=models.CASCADE, related_name="deliveries")
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE, related_name="deliveries")
    sent_at = models.DateTimeField(auto_now_add=True)
    error = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["newsletter", "subscriber"], name="uniq_delivery")]
