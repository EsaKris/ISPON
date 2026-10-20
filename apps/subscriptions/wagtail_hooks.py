from django.urls import path, reverse_lazy
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from .admin_views import manage


@hooks.register("register_admin_urls")
def urls():
    return [path("newsletter/send/", manage, name="newsletter_manage")]


class SendMenuItem(MenuItem):
    def is_shown(self, request):
        return request.user.has_perm("subscriptions.change_newsletter")


@hooks.register("register_admin_menu_item")
def menu():
    return SendMenuItem("Send newsletters", reverse_lazy("newsletter_manage"), icon_name="mail", order=210)
