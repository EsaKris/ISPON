from django.urls import path, reverse_lazy
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.images.permissions import permission_policy

from .admin_views import bulk_upload


@hooks.register("register_admin_urls")
def urls():
    return [path("gallery/upload/", bulk_upload, name="gallery_bulk_upload")]


class UploadMenuItem(MenuItem):
    def is_shown(self, request):
        return permission_policy.user_has_permission(request.user, "add")


@hooks.register("register_admin_menu_item")
def menu():
    return UploadMenuItem("Upload photos", reverse_lazy("gallery_bulk_upload"), icon_name="upload", order=125)
