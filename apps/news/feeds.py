import datetime

from django.contrib.syndication.views import Feed
from django.utils import timezone

from .models import BlogPostPage


class BlogFeed(Feed):
    title = "ISPON News and Blog"
    link = "/blog/"
    description = "News, notices and updates from the Institute of Safety Professionals of Nigeria."

    def items(self):
        return BlogPostPage.objects.live().order_by("-publication_date", "-pk")[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt

    def item_link(self, item):
        return item.url

    def item_pubdate(self, item):
        return timezone.make_aware(datetime.datetime.combine(item.publication_date, datetime.time()))
