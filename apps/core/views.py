from django.core.paginator import Paginator
import datetime

from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from wagtail.models import Page

from .seo import logo_url


def search(request):
    """Site-wide search over live, public pages (including news articles)."""
    q = request.GET.get("q", "").strip()[:100]
    results = None
    if q:
        results = Paginator(list(Page.objects.live().public().not_type(Page).search(q)), 10).get_page(request.GET.get("page"))
    return render(request, "search.html", {"q": q, "results": results, "noindex": True, "seo_title": "Search"})


def favicon(request):
    return redirect(logo_url("fill-48x48|format-png"))


def manifest(request):
    from .seo import site_settings

    s = site_settings(request)
    icons = [{"src": logo_url(f"fill-{n}x{n}|format-png"), "sizes": f"{n}x{n}", "type": "image/png" if s.logo else "image/svg+xml"} for n in (192, 512)] if s.logo else [
        {"src": logo_url(), "sizes": "any", "type": "image/svg+xml"}]
    return JsonResponse({"name": "Institute of Safety Professionals of Nigeria", "short_name": "ISPON", "start_url": "/", "display": "browser",
                         "theme_color": s.theme_color, "background_color": "#f1eee6", "lang": "en-NG", "icons": icons},
                        content_type="application/manifest+json")


def security_txt(request):
    """RFC 9116 contact file for people who find a vulnerability. The expiry date rolls forward automatically."""
    from .seo import site_settings

    s = site_settings(request)
    expires = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=300)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    host = request.build_absolute_uri("/").rstrip("/")
    body = (f"Contact: mailto:{s.email or 'info@ispon.gov.ng'}\nExpires: {expires}\nPreferred-Languages: en\n"
            f"Canonical: {host}/.well-known/security.txt\nPolicy: {host}/terms-of-use/\n")
    return HttpResponse(body, content_type="text/plain; charset=utf-8")
