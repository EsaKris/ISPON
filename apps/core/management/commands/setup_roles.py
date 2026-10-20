"""Create editor roles with least-privilege permissions."""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from wagtail.models import Collection, GroupCollectionPermission, GroupPagePermission, Page


def perm(app, code):
    return Permission.objects.get(content_type__app_label=app, codename=code)


class Command(BaseCommand):
    help = "Create Content Administrator, Gallery Manager and Branch & Team Manager groups."

    def handle(self, *args, **opts):
        root, coll = Page.objects.get(depth=1), Collection.get_first_root_node()
        access = perm("wagtailadmin", "access_admin")
        page_codes = ["add_page", "change_page", "publish_page", "lock_page", "unlock_page"]
        media = [perm("wagtailimages", c) for c in ("add_image", "change_image", "choose_image")] + [
            perm("wagtaildocs", c) for c in ("add_document", "change_document", "choose_document")]

        def group(name, page_root=None, model_perms=(), media_access=False):
            g, _ = Group.objects.get_or_create(name=name)
            g.permissions.set([access, *model_perms])
            GroupPagePermission.objects.filter(group=g).delete()
            GroupCollectionPermission.objects.filter(group=g).delete()
            if page_root:
                for c in page_codes:
                    GroupPagePermission.objects.create(group=g, page=page_root, permission=perm("wagtailcore", c))
            if media_access:
                for p in media:
                    GroupCollectionPermission.objects.create(group=g, collection=coll, permission=p)
            return g

        gallery = Page.objects.filter(slug="gallery").first()
        group("Content Administrator", root, media_access=True)
        group("Gallery Manager", gallery, media_access=True)
        group("Branch & Team Manager", None, [perm("organisation", f"{a}_{m}") for m in ("branch", "teammember") for a in ("add", "change", "delete")], True)
        group("Newsletter Manager", None, [perm("subscriptions", f"{a}_newsletter") for a in ("add", "change", "view", "delete")] + [perm("subscriptions", "view_subscriber")])
        self.stdout.write(self.style.SUCCESS("Roles created."))
