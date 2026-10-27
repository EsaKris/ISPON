"""Bring an EXISTING database up to the current design and page types. Safe to run more than once.

What it does:
  - turns an old plain About Us / Membership Procedure page (StandardPage) into the designed page types,
    keeping the old page as an unpublished draft ("-previous") so nothing is lost;
  - adds the Services, Careers and FAQ pages if missing;
  - fills homepage sections that are still empty (highlights, numbers, headings) and blank site settings.
It never overwrites text you have already edited.
"""
from django.core.management.base import BaseCommand, CommandError

from apps.core.management.commands import seed_site as sd
from apps.core.models import HeroSlide, AboutExpert, AboutPage, HomePage, MembershipPage, Pillar, SiteSettings, Statistic, StandardPage
from apps.core.models import CareerPage, FAQPage, ServicesPage
from apps.organisation.models import TeamMember
from apps.core.legal_content import PAGES as LEGAL_PAGES
from wagtail.models import Site


class Command(BaseCommand):
    help = "Upgrade an existing site to the current page designs."

    def handle(self, *args, **opts):
        home = HomePage.objects.first()
        if not home:
            raise CommandError("No homepage found. For a brand new site run: python manage.py seed_site")
        done = []

        def add(model, title, slug, kwargs):
            menu = kwargs.pop("menu", True)
            page = home.add_child(instance=model(title=title, slug=slug, show_in_menus=menu, **({} if menu else {"show_in_footer": True}), **kwargs))
            page.save_revision().publish()
            return page

        # 1. convert plain pages to designed page types, keeping the old page as an unpublished draft
        for slug, model, title, kw in [("about-us", AboutPage, "About Us", sd.about_kwargs), ("membership-procedure", MembershipPage, "Membership Procedure", sd.membership_kwargs)]:
            old = home.get_children().filter(slug=slug).first()
            if old and old.specific_class is StandardPage:
                old = old.specific
                old.slug, old.show_in_menus = slug + "-previous", False
                old.save()
                old.unpublish()
                new = add(model, title, slug, kw())
                new.move(old, pos="left")  # same place in the menu order
                done.append(f"{title}: converted (old version kept as unpublished '{slug}-previous')")
            elif not old:
                add(model, title, slug, kw())
                done.append(f"{title}: created")
        # experts on the About page
        about = AboutPage.objects.first()
        if about and not about.experts.exists():
            for i, key in enumerate(("Udezi", "Onuoha", "Nwosu", "Modebe")):
                m = TeamMember.objects.filter(name__contains=key).first()
                if m:
                    AboutExpert.objects.create(page=about, member=m, sort_order=i)
            about.save_revision().publish()
            done.append("About Us: experts added")
        # 2. missing pages
        for model, title, slug, kw in [(ServicesPage, "Our Services", "services", sd.services_kwargs), (CareerPage, "Careers", "careers", sd.careers_kwargs), (FAQPage, "FAQ", "faq", sd.faq_kwargs)]:
            if not model.objects.exists():
                add(model, title, slug, kw())
                done.append(f"{title}: created")
        for title_, slug_, body_ in LEGAL_PAGES:
            if not home.get_children().filter(slug=slug_).exists():
                kw = sd.legal_kwargs(body_)
                menu, footer = kw.pop("menu"), kw.pop("footer")
                page = home.add_child(instance=StandardPage(title=title_, slug=slug_, show_in_menus=menu, show_in_footer=footer, intro="Last updated 26 October 2026", **kw))
                page.save_revision().publish()
                done.append(f"{title_}: created")
        # 3. empty homepage sections (never overwrites edited text)
        changed = False
        for i, (t, d) in enumerate(sd.PILLARS):
            if not home.pillars.exists():
                Pillar.objects.create(page=home, title=t, description=d, sort_order=i)
                changed = True
        if not home.statistics.exists():
            for i, (lab, val, suf) in enumerate(sd.STATS):
                Statistic.objects.create(page=home, label=lab, value=val, suffix=suf, visible=True, sort_order=i)
            changed = True
        if not home.hero_slides.exists():
            HeroSlide.objects.create(page=home, kind="flashlight", kicker="Institute of Safety Professionals of Nigeria", headline=home.hero_headline, text=home.hero_text,
                                     cta_label=home.cta_label, cta_url=home.cta_url, cta2_label=home.cta2_label, cta2_url=home.cta2_url)
            changed = True
        for field, value in [("proud_heading", "46 years of experience"), ("services_intro", "Our core services include safety training, professional certification, consultancy, advocacy, and industry collaboration to promote safe and compliant workplaces."),
                             ("team_intro", "Meet our team of experienced safety professionals dedicated to delivering expert guidance, training, and solutions that ensure workplace safety and compliance.")]:
            if not getattr(home, field):
                setattr(home, field, value)
                changed = True
        if changed:
            home.save_revision().publish()
            done.append("Home: empty sections filled")
        # 4. blank site settings
        s = SiteSettings.for_site(Site.objects.get(is_default_site=True))
        for field, value in [("newsletter_text", "Subscribe to our Newsletter to be updated. We promise not to spam."), ("header_button_label", "Register Now"), ("header_button_url", sd.EVENT_URL),
                             ("twitter_handle", "@isponng_safety"), ("default_description", "The recognized professional body regulating safety professionals and promoting workplace safety in Nigeria.")]:
            if not getattr(s, field):
                setattr(s, field, value)
                s.save()
                done.append(f"Site settings: {field} set")
        self.stdout.write(self.style.SUCCESS("\n".join(done) if done else "Already up to date."))
        self.stdout.write("Next: python manage.py collectstatic --noinput, then restart the app.")
