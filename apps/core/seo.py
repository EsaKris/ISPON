"""Page metadata, social sharing tags, geo tags and schema.org JSON-LD."""
import json

from django.templatetags.static import static
from django.utils.html import strip_tags
from django.utils.text import Truncator
from wagtail.models import Site

from .models import SiteSettings

DEFAULT_DESC = "The recognized professional body regulating safety professionals and promoting workplace safety in Nigeria."
NAME = "Institute of Safety Professionals of Nigeria"
ROBOTS = "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"


def _abs(request, url):
    return url if url.startswith("http") else request.build_absolute_uri(url)


def site_settings(request):
    site = Site.find_for_request(request)
    return SiteSettings.for_site(site) if site else (SiteSettings.objects.first() or SiteSettings())


def _img(request, image, spec, alt):
    r = image.get_rendition(spec)
    return {"url": _abs(request, r.url), "width": r.width, "height": r.height, "alt": alt}


def share_image(request, page, s):
    for attr in ("social_image", "featured_image", "cover", "intro_image"):
        im = getattr(page, attr, None) if page else None
        if im:
            return _img(request, im, "fill-1200x630|format-jpeg", page.title)
    if s.default_share_image:
        return _img(request, s.default_share_image, "fill-1200x630|format-jpeg", NAME)
    if s.logo:
        return _img(request, s.logo, "max-600x600|format-png", "ISPON logo")
    return None


def describe(page, s):
    if page:
        text = page.search_description or ""
        for attr in ("excerpt", "intro", "description", "hero_text"):
            if not text:
                text = str(getattr(page, attr, "") or "")
        text = strip_tags(text).strip()
        if text:
            return Truncator(text).chars(158)
    return s.default_description or DEFAULT_DESC


def head(request, page=None, noindex=False, title=None):
    s, site = site_settings(request), Site.find_for_request(request)
    is_home = bool(page and site and page.pk == site.root_page_id)
    if page:
        t = (page.seo_title or "ISPON | " + NAME) if is_home else f"{page.seo_title or page.title} | ISPON"
        canonical = getattr(page, "canonical_url", "") or page.full_url or request.build_absolute_uri(request.path)
    else:
        t, canonical = f"{title or 'ISPON'} | ISPON", request.build_absolute_uri(request.path)
    m = {"s": s, "page": page, "title": t, "canonical": canonical, "description": describe(page, s),
         "robots": "noindex,follow" if (noindex or request.GET) else ROBOTS, "image": share_image(request, page, s),
         "type": "article" if hasattr(page, "publication_date") else "website", "is_home": is_home, "base": request.build_absolute_uri("/").rstrip("/"),
         "lat": s.geo_latitude, "lng": s.geo_longitude}
    if m["type"] == "article":
        m["published"] = page.publication_date.isoformat()
        m["modified"] = (page.last_published_at or page.latest_revision_created_at).isoformat() if (page.last_published_at or page.latest_revision_created_at) else ""
        m["tags"] = [tg.name for tg in page.tags.all()]
    m["graph"] = graph(request, m)
    return m


def organization(request, m):
    s, base = m["s"], m["base"]
    org = {"@type": "Organization", "@id": base + "/#organization", "name": NAME, "alternateName": "ISPON", "url": base + "/",
           "areaServed": {"@type": "Country", "name": "Nigeria"}}
    if s.logo:
        r = s.logo.get_rendition("max-600x600|format-png")
        org["logo"] = {"@type": "ImageObject", "url": _abs(request, r.url), "width": r.width, "height": r.height}
    if s.address:
        org["address"] = {"@type": "PostalAddress", "streetAddress": " ".join(s.address.split()), "addressLocality": s.geo_placename,
                          "addressRegion": s.address_region, "addressCountry": "NG"}
    if s.phone:
        org["telephone"] = s.phone
    if s.email:
        org["email"] = s.email
    same = [u for u in (s.facebook, s.x_twitter, s.instagram) if u]
    if same:
        org["sameAs"] = same
    if s.geo_latitude is not None and s.geo_longitude is not None:
        org["geo"] = {"@type": "GeoCoordinates", "latitude": float(s.geo_latitude), "longitude": float(s.geo_longitude)}
    return org


def graph(request, m):
    from apps.gallery.models import AlbumPage
    from apps.organisation.models import Branch, ContactPage, TeamMember, TeamPage

    page, base, s = m["page"], m["base"], m["s"]
    org = organization(request, m)
    g = [org, {"@type": "WebSite", "@id": base + "/#website", "url": base + "/", "name": "ISPON", "inLanguage": "en-NG",
               "publisher": {"@id": org["@id"]},
               "potentialAction": {"@type": "SearchAction", "target": base + "/search/?q={search_term_string}", "query-input": "required name=search_term_string"}}]
    if not page:
        return g
    url = m["canonical"]
    kind = "WebPage"
    if isinstance(page, ContactPage):
        kind = "ContactPage"
    elif page.slug == "about-us":
        kind = "AboutPage"
    elif hasattr(page, "publication_date"):
        kind = "NewsArticle"
    node = {"@type": kind, "@id": url + "#webpage", "url": url, "name": page.seo_title or page.title, "description": m["description"],
            "inLanguage": "en-NG", "isPartOf": {"@id": base + "/#website"}, "publisher": {"@id": org["@id"]}}
    if page.last_published_at:
        node["dateModified"] = page.last_published_at.isoformat()
    if m["image"]:
        node["image"] = m["image"]["url"]
    if kind == "NewsArticle":
        node.update({"headline": page.title, "datePublished": m["published"], "mainEntityOfPage": url,
                     "author": {"@type": "Organization", "name": page.author_name}, "keywords": ", ".join(m["tags"]) or None,
                     "articleSection": page.category.name if page.category else None})
        node = {k: v for k, v in node.items() if v}
    if isinstance(page, AlbumPage):
        node["@type"] = "ImageGallery"
        node["image"] = [{"@type": "ImageObject", "contentUrl": _abs(request, ai.image.get_rendition("width-1600").url), "name": ai.title,
                          "description": ai.description or ai.alt_text} for ai in page.published_images()[:20]]
    if isinstance(page, ContactPage):
        node["about"] = {"@id": org["@id"]}
        org["subOrganization"] = [{"@type": "Organization", "name": b.name, "telephone": b.phone or None, "email": b.email or None,
                                   "address": {"@type": "PostalAddress", "streetAddress": b.address or None, "addressRegion": b.state, "addressCountry": "NG"}}
                                  for b in Branch.objects.filter(is_published=True)]
        org["subOrganization"] = [{k: v for k, v in d.items() if v} for d in org["subOrganization"]]
    from apps.core.models import FAQPage

    if isinstance(page, FAQPage):
        node["@type"] = "FAQPage"
        node["mainEntity"] = [{"@type": "Question", "name": q.question, "acceptedAnswer": {"@type": "Answer", "text": strip_tags(str(q.answer))}}
                              for q in page.items.all() if q.visible]
    g.append(node)
    if isinstance(page, TeamPage):
        people = TeamMember.objects.published().current()
        g.append({"@type": "ItemList", "name": "ISPON leadership", "itemListElement": [
            {"@type": "ListItem", "position": i, "item": {"@type": "Person", "name": p.name, "jobTitle": p.designation, "worksFor": {"@id": org["@id"]}}}
            for i, p in enumerate(people, 1)]})
    if not m["is_home"]:
        site = Site.find_for_request(request)
        chain = [a for a in page.get_ancestors().live() if site and a.depth >= site.root_page.depth] + [page]
        g.append({"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i, "name": "Home" if site and a.pk == site.root_page_id else a.title,
             "item": _abs(request, a.url) if a.pk != page.pk else url} for i, a in enumerate(chain, 1)]})
    return g


def jsonld(m):
    return json.dumps({"@context": "https://schema.org", "@graph": m["graph"]}, ensure_ascii=False, default=str).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def logo_url(spec="max-200x200|format-png"):
    s = SiteSettings.objects.exclude(logo=None).first()
    return s.logo.get_rendition(spec).url if s else static("img/ispon-shield.svg")
