"""ISPON admin panel: grouped menus, News and Albums listings, dashboard quick actions, colour theme."""
from django.templatetags.static import static
from django.shortcuts import redirect
from django.urls import NoReverseMatch, path, reverse, reverse_lazy
from wagtail.admin.menu import MenuItem
from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin.ui.components import Component
from wagtail.admin.viewsets.pages import PageListingViewSet
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from apps.gallery.models import AlbumPage, GalleryIndexPage
from apps.news.models import BlogIndexPage, BlogPostPage
from apps.organisation.models import Branch, ContactSubmission, TeamMember
from apps.subscriptions.models import Newsletter, Subscriber


class NewsListing(PageListingViewSet):
    icon, menu_label, model, menu_order, add_to_admin_menu = "doc-full", "News", BlogPostPage, 110, True


class AlbumListing(PageListingViewSet):
    icon, menu_label, model, menu_order, add_to_admin_menu = "image", "Photo albums", AlbumPage, 120, True


@hooks.register("register_admin_viewset")
def register_news():
    return NewsListing("news_articles")


@hooks.register("register_admin_viewset")
def register_albums():
    return AlbumListing("photo_albums")


class TeamViewSet(SnippetViewSet):
    model, icon = TeamMember, "user"
    list_display = ["name", "designation", "is_published", "featured", "is_former", "order"]
    list_filter = ["is_published", "featured", "is_former"]


class BranchViewSet(SnippetViewSet):
    model, icon = Branch, "site"
    list_display = ["name", "state", "contact_person", "phone", "is_published", "featured"]
    list_filter = ["state", "is_published", "featured"]


class SubmissionViewSet(SnippetViewSet):
    model, icon = ContactSubmission, "mail"
    menu_label = "Contact messages"
    list_display = ["subject", "name", "email", "created_at", "is_read"]
    list_filter = ["is_read"]


class SubscriberViewSet(SnippetViewSet):
    model, icon = Subscriber, "group"
    list_display = ["email", "confirmed_at", "is_active", "consented_at", "unsubscribed_at"]
    list_filter = ["is_active"]


class NewsletterViewSet(SnippetViewSet):
    model, icon = Newsletter, "mail"
    list_display = ["subject", "status", "created_at", "sent_at"]


class PeopleGroup(SnippetViewSetGroup):
    items = (TeamViewSet, BranchViewSet, SubmissionViewSet, SubscriberViewSet, NewsletterViewSet)
    menu_label, menu_icon, menu_name, menu_order = "People & contacts", "group", "people", 200


register_snippet(PeopleGroup)


class QuickActions(Component):
    order = 5
    template_name = "wagtailadmin/home/quick_actions.html"

    def get_context_data(self, parent_context):
        from apps.core.models import MembershipPage

        links = []

        def add(label, name, *args):
            try:
                links.append((label, reverse(name, args=args)))
            except NoReverseMatch:
                pass

        add("Edit the homepage", "edit_homepage")
        blog, gal, mem = BlogIndexPage.objects.first(), GalleryIndexPage.objects.first(), MembershipPage.objects.first()
        if blog:
            add("Write a news article", "wagtailadmin_pages:add", "news", "blogpostpage", blog.pk)
        if gal:
            add("Create a photo album", "wagtailadmin_pages:add", "gallery", "albumpage", gal.pk)
        add("Upload photos to an album", "gallery_bulk_upload")
        if mem:
            add("Edit membership text and fees", "wagtailadmin_pages:edit", mem.pk)
        add("Send a newsletter", "newsletter_manage")
        add("Add a team member", "wagtailsnippets_organisation_teammember:add")
        add("Add a branch", "wagtailsnippets_organisation_branch:add")
        return {"links": links}


@hooks.register("construct_homepage_panels")
def add_quick_actions(request, panels):
    panels.insert(0, QuickActions())


@hooks.register("insert_global_admin_css")
def admin_css():
    return format_html('<link rel="stylesheet" href="{}">', static("css/admin.css"))


def edit_homepage(request):
    from apps.core.models import HomePage

    home = HomePage.objects.first()
    return redirect(reverse("wagtailadmin_pages:edit", args=(home.pk,))) if home else redirect("wagtailadmin_home")


@hooks.register("register_admin_urls")
def homepage_urls():
    return [path("homepage/", edit_homepage, name="edit_homepage")]


class HomepageMenuItem(MenuItem):
    def is_shown(self, request):
        from apps.core.models import HomePage

        home = HomePage.objects.first()
        return bool(home and home.permissions_for_user(request.user).can_edit())


@hooks.register("register_admin_menu_item")
def homepage_menu():
    return HomepageMenuItem("Homepage", reverse_lazy("edit_homepage"), icon_name="home", order=90)
