"""Admin tool: upload many photos at once into a gallery album."""
import hashlib
import io
import re
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.shortcuts import redirect, render
from django.urls import reverse
from PIL import Image as PILImage
from wagtail.admin.auth import require_admin_access
from wagtail.images import get_image_model
from wagtail.images.permissions import permission_policy

from .models import AlbumImage, AlbumPage

EXTS, FORMATS, MAX_FILES = {"jpg", "jpeg", "png", "webp", "gif"}, {"JPEG", "PNG", "WEBP", "GIF"}, 30


def _check(f):
    """Return (bytes, error, (width, height)). Never trusts the filename or browser MIME type alone."""
    if Path(f.name).suffix.lower().lstrip(".") not in EXTS:
        return None, "unsupported file type", None
    if f.size > settings.WAGTAILIMAGES_MAX_UPLOAD_SIZE:
        return None, "file is too large", None
    data = f.read()
    try:
        with PILImage.open(io.BytesIO(data)) as im:
            fmt, size = im.format, im.size
            im.verify()
    except Exception:
        return None, "not a valid image", None
    return (data, None, size) if fmt in FORMATS else (None, "unsupported image format", None)


@require_admin_access
def bulk_upload(request):
    user = request.user
    if not permission_policy.user_has_permission(user, "add"):
        raise PermissionDenied
    albums = [a for a in AlbumPage.objects.order_by("title") if a.permissions_for_user(user).can_edit()]
    if request.method == "POST":
        album = next((a for a in albums if str(a.pk) == request.POST.get("album")), None)
        files = request.FILES.getlist("photos")
        credit = request.POST.get("credit", "").strip()[:120]
        if not album:
            messages.error(request, "Choose an album you are allowed to edit.")
        elif not files or len(files) > MAX_FILES:
            messages.error(request, f"Choose between 1 and {MAX_FILES} photos.")
        else:
            Image, obj, added, skipped = get_image_model(), album.get_latest_revision_as_object(), 0, []
            have = {ai.image_id for ai in obj.images.all()}
            for f in files:
                data, err, size = _check(f)
                if err:
                    skipped.append(f"{f.name}: {err}")
                    continue
                digest = hashlib.sha1(data, usedforsecurity=False).hexdigest()
                img = Image.objects.filter(file_hash=digest).first()  # reuse identical uploads
                if not img:
                    img = Image(title=Path(f.name).stem[:255], uploaded_by_user=user, file_hash=digest, file_size=len(data))
                    img.file.save(re.sub(r"[^A-Za-z0-9._-]", "_", Path(f.name).name)[:80], ContentFile(data), save=False)
                    img.width, img.height = size  # set after the file is attached, which resets them
                    img.save()
                if img.pk in have:
                    skipped.append(f"{f.name}: already in this album")
                    continue
                title = re.sub(r"[_-]+", " ", Path(f.name).stem).strip().capitalize()[:120] or "Photo"
                have.add(img.pk)
                obj.images.add(AlbumImage(image=img, title=title, alt_text=title, credit=credit, is_published=True, sort_order=len(have)))
                added += 1
            if added:
                rev = obj.save_revision(user=user)
                if album.live:
                    rev.publish()
                messages.success(request, f"{added} photo(s) added to \u2018{album.title}\u2019. Edit each photo\u2019s title, description and alt text in the album editor.")
            for s in skipped:
                messages.warning(request, f"Skipped {s}")
            if added:
                return redirect(reverse("wagtailadmin_pages:edit", args=(album.pk,)))
    return render(request, "gallery/admin/bulk_upload.html", {"albums": albums, "max_files": MAX_FILES})
