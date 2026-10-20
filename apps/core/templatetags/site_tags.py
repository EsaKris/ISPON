from django import template
from django.utils.safestring import mark_safe
from wagtail.models import Site

from apps.core import seo as seo_mod

register = template.Library()


@register.simple_tag(takes_context=True)
def nav_items(context):
    """Main navigation: site root plus its live children flagged 'show in menus'."""
    site = Site.find_for_request(context["request"])
    if not site:
        return []
    root = site.root_page.specific
    cur = context.get("page")
    items = [root, *root.get_children().live().in_menu().specific()]
    out = []
    for i in items:
        is_root = i.pk == root.pk
        active = bool(cur and hasattr(cur, "pk") and (cur.pk == i.pk or (not is_root and cur.is_descendant_of(i))))
        out.append({"title": "Home" if is_root else i.title, "url": i.url, "active": active})
    return out


@register.filter
def split_phones(value):
    """Split a comma-separated phone field into separate numbers so each gets its own tel: link."""
    return [n.strip() for n in (value or "").split(",") if n.strip()]


@register.simple_tag(takes_context=True)
def seo(context):
    page = context.get("page")
    return seo_mod.head(context["request"], page if hasattr(page, "pk") else None, context.get("noindex", False), context.get("seo_title"))


@register.simple_tag
def jsonld(m):
    return mark_safe('<script type="application/ld+json">' + seo_mod.jsonld(m) + "</script>")


@register.simple_tag
def logo_url(spec="max-200x200|format-png"):
    """URL of the logo uploaded in Site settings, or the built-in ISPON shield."""
    return seo_mod.logo_url(spec)


@register.simple_tag(takes_context=True)
def footer_pages(context):
    """Live pages flagged 'show in footer' (Services, Careers, FAQ...), directly under the site root."""
    site = Site.find_for_request(context["request"])
    if not site:
        return []
    return [{"title": p.title, "url": p.url} for p in site.root_page.get_children().live().specific() if getattr(p, "show_in_footer", False)]
