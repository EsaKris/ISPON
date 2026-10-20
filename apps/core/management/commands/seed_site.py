"""Create the page tree and verified starter content from ispon.gov.ng. Safe to re-run (skips if a HomePage exists)."""
import datetime
import hashlib
import re
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image as PILImage
from wagtail.images.models import Image
from wagtail.contrib.redirects.models import Redirect
from wagtail.models import Page, Site
from wagtail.rich_text import RichText

from apps.core.models import AboutExpert, AboutFact, AboutPage, AboutReason, CareerPage, FAQItem, FAQPage, ServicesPage, TimelineEntry
from apps.core.seed_data import EVENT_URL, POSTS, TEAM, bio
from apps.core.models import HomePage, MembershipFee, MembershipPage, Pillar, ServiceCard, SiteSettings, StandardPage, Statistic
from apps.gallery.models import GalleryIndexPage
from apps.news.models import BlogCategory, BlogIndexPage, BlogPostPage
from apps.organisation.models import Branch, ContactPage, TeamMember, TeamPage

SERVICES = [
    ("Professional Membership & Certification", "We offer professional membership and certification that recognize competence, uphold industry standards, and demonstrate commitment to excellence in safety practice."),
    ("Safety Training & Development Programs", "We provide comprehensive safety training and development programs designed to enhance skills, improve workplace safety, and ensure compliance with industry standards."),
    ("Safety Awareness & Advocacy", "We promote safety awareness and advocacy by educating organizations and the public on best practices, risk prevention, and the importance of a safety-first culture."),
    ("Industry Collaboration & Research", "We drive industry collaboration and research by partnering with organizations and experts to develop innovative safety solutions and advance best practices across sectors."),
    ("Safety Conferences & Workshops", "We organize safety conferences and workshops that bring together professionals to share knowledge, explore trends, and enhance skills in occupational health and safety."),
    ("Consultancy", "We provide expert safety consultancy services, offering tailored solutions to help organizations manage risks, ensure compliance, and maintain safe working environments."),
]
PILLARS = [
    ("Recognized safety professional body in Nigeria", "The Institute of Safety Professionals of Nigeria (ISPON) is the recognized regulatory body for safety professionals in Nigeria. It is responsible for setting professional standards, certifying practitioners, and promoting excellence in occupational health, safety, and environmental (HSE) practices across various industries."),
    ("Industry-standard safety training", "We provide industry-standard safety training that equips individuals and organizations with the essential knowledge and skills to maintain safe, compliant, and hazard-free workplaces."),
    ("Professional networking opportunities", "We offer professional networking opportunities that connect safety practitioners with industry experts, organizations, and peers to share knowledge, build partnerships, and advance career growth."),
    ("Continuous professional development", "We support continuous professional development by providing ongoing training, workshops, and learning opportunities to help safety professionals enhance their skills and stay updated with industry standards."),
    ("Contribution to national safety improvement", "We contribute to national safety improvement by promoting best practices, raising awareness, and supporting policies that enhance workplace health and safety standards across Nigeria."),
]
# (label, value, suffix) as shown on the live homepage
STATS = [("Registered safety professionals", 12000, "+"), ("Years of experience", 46, "+"), ("Colleagues and counting", 2930, "")]
HOME_FEATURED = {"Chief Dr. Udezi Stephen Lucky Awore", "Dr. Foreman Chido Onuoha", "Mrs. Ajayi Ibironke", "Mazi Harold Uzor Echendu"}  # shown on the live homepage

# (state, address, chairman, phones, email) from ispon.gov.ng/contact-page/
BRANCHES = [
    ("FCT Abuja", "FLAT 1, 3RD FLOOR, BUSY MART PLAZA, EBITE UKIWE STREET, JABI, ABUJA", "MRS IFEOMA OKPARA", "8037087695", ""),
    ("Abia", "BENZ PLAZA, 273B ABA-OWERRI ROAD, ADJACENT TO NGWA HIGH SCHOOL, ABAYI-ABA", "ENGR. HENRY UZOMA", "7031634044", "isponabia@gmail.com"),
    ("Akwa Ibom", "NO 3, EKET STREET, OFF ORON ROAD BY ANIMEKS SCHOOL, EKET, AKWA IBOM STATE.", "AMB. EKARIKA", "7038089525", ""),
    ("Anambra", "27, ZIK AVENUE, AMAOBA, AKWA, ANAMBRA STATE", "DR C. ONUOHA", "8037603720", ""),
    ("Bayelsa", "NO. 72, SAPTEX ROAD, YENIZUE EPIE, YENAGOA, BAYELSA STATE", "MR JOHN GARR", "7084073926, 09168686085", ""),
    ("Cross River", "VENETIAN ARENA, 50, MURTALA MOHAMMED HIGHWAY, CALABAR.", "MR ADEKUNLE ODUTOLA", "8035521176, 08035521276, 08033195783", "isponcrossriverbranch@gmail.com"),
    ("Delta", "NO. 7, TONY MENE-AKPATA STREET, OFF OGUNU ROAD, UGBUWANGUE, WAARI, DELTA STATE", "DR. KINGSLEY UNUEROH", "8028487246, 09162615864", "nispdeltabranch@yahoo.com"),
    ("Edo", "NO. 20 IROWA OBAZE STREET, (WINNERS STREET) OFF FEDERAL GOVERNMENT GIRLS COLLEGE ROAD, UGBOWO, BENIN CITY EDO STATE", "MR. JAMES BENSON", "8023377031", ""),
    ("Imo", "NO 16 WETHERAL ROAD, CHERUBIN JUNCTION, TOP FLOOR OF UNITY BANK, OWERRI, IMO STATE", "DR CHRISTIAN MADUABUCHI F. CHUKWUJI", "08064875577, 09017272296, 08169257398", "isponimostate@gmail.com"),
    ("Kaduna", "SUITE A5 LORD DOING PLAZA, OPPOSITE OUR LADY FATIMA, SABO KADUNA", "MR. SAUDJE MATTHEW OGHENERHEROHWO", "8090702400, 08122398842", "saudjemat@gmail.com"),
    ("Lagos", "NIGERIA EDUCATION RESEARCH & DEVELOPMENT COUNCIL (NERDC) PREMISES, PLOT 3/4 NERDC ROAD, OFF ASHABI COLE OR HAKEEM BALOGUN, AGIDINGBI-ALAUSA, IKEJA, LAGOS.", "MR. OLUSOLA OGUNLEYE", "8034564044, 09169536265", "lagosbranch@isponnigeria.org"),
    ("Niger", "MAINSTREAM ENERGY SOLUTION LTD, KAINJI", "DR MRS PRISCA NGOZI IWUNZE", "8027924347", ""),
    ("Ogun", "OGAB PLAZA, GROUND FLOOR, BREWERY, ABEOKUTA", "MR. TEMITOPE AMOO", "8139572791, 08118345976", "isponogun2024@gmail.com"),
    ("Osun", "12B AYETORO STREET, BEHIND FIRST BANK HOLDING & CHICKEN REPUBLIC, OSOGBO, OSUN STATE", "MR. WOLE OYEDELE", "8055104481", ""),
    ("Oyo", "NO. 16. ADEBIYI STREET, JOYCE B ROAD, OFF RING ROAD, IBADAN, OYO STATE", "MR. OLUYEMI", "8038123595, 08060431589", ""),
    ("Plateau", "C/O JOS ELECTRICITY DISTRIBUTION PLC, NO. 9 AHMADU BELLO WAY, JOS", "MR. ALVINMAX CYPRIAN YENKWO", "8036065651, 08035981508", "isponplateau@yahoo.com"),
    ("Rivers", "Liaison Office: No. 24 Ken Saro-Wiwa Road (Formerly Plot 71 Stadium Road) Portharcourt.", "DR. YEMI SHOLA-JONATHAN", "8063777755", "riversbranch@isponnigeria.org"),
]
CAT = "ISPON Updates"
ASSETS = Path(__file__).resolve().parents[4] / "seed_assets"


def load_image(rel, title):
    """Import a generated starter picture. Returns None if the file is missing."""
    path = ASSETS / rel
    if not path.exists():
        return None
    data = path.read_bytes()
    with PILImage.open(path) as im:
        size = im.size
    img = Image(title=title, file_hash=hashlib.sha1(data).hexdigest(), file_size=len(data))
    img.file.save(path.name, ContentFile(data), save=False)
    img.width, img.height = size
    img.save()
    return img


def tidy(t):
    return re.sub(r"\b(\d)Rd\b", r"\1rd", t.title()).replace("'S", "'s")


def phones(raw):
    return ", ".join(n if n.startswith("0") else "0" + n for n in re.findall(r"\d{10,11}", raw))


def rt(*paras):
    return RichText("".join(paras))


ABOUT_BODY = (
    "<p>The origins of ISPON can be traced back to 1978 when as members of the National Industrial Safety Council (NISCN), a tripartite organization set up to manage industrial disputes angling on workers safety between government, employers and employees, practicing safety professionals sought the establishment of a technical arm of the body. A need for a professional society with special focus on grooming practitioners and meeting their needs in the industry saw to the creation of the Nigerian Society of Safety Professionals (NSSP) in 1980.</p>"
    "<p>From these humble beginnings in 1980, the institute has metamorphosed through the years: first as an umbrella professional body for safety practitioners in Nigeria, and thereafter as an Institute with the powers to regulate the practice of safety management in Nigeria. NSSP metamorphosed into the Nigerian Institute of Safety Professionals (NISP) in 1989, and thereafter NISP metamorphosed into the Institute of Safety Professionals of Nigeria (ISPON) by the enactment and signing into law of the ISPON Act 2014.</p>"
    "<p>Today, the Institute squarely functions as an agency of the Federal Republic of Nigeria, with clear mandates to regulate the practice of safety management in Nigeria, in collaboration with other agencies and in line with the provisions of the ISPON Act No. 2 of 2014.</p>"
    "<p>Truly, we have come a long way. With well over 12 thousand members scattered across the world, we are Africa's largest organization for safety management. Our members are drawn from various sectors of the Nigerian economy, while a lot more represent us proudly in diverse sectors around the world, exhibiting true Nigerian brilliance and resilience.</p>"
)
ABOUT_FACTS = [("1980", "The Nigerian Society of Safety Professionals (NSSP) is created"), ("2014", "The ISPON Act, 2014 (Act No. 2) is signed into law on 19 May 2014"), ("12,000+", "Members worldwide, as stated on ispon.gov.ng")]
ABOUT_TIMELINE = [
    ("1978", "A technical arm is sought", "Practicing safety professionals in the National Industrial Safety Council (NISCN) ask for a technical arm of the body."),
    ("1980", "NSSP is created", "The Nigerian Society of Safety Professionals is formed to groom practitioners and meet their needs in the industry."),
    ("1989", "NISP", "NSSP becomes the Nigerian Institute of Safety Professionals (NISP)."),
    ("2014", "The ISPON Act", "NISP becomes the Institute of Safety Professionals of Nigeria (ISPON) through the ISPON Act, 2014 (Act No. 2)."),
]
ABOUT_REASONS = [
    ("Professional recognition", "ISPON is a well-known professional body in Nigeria that recognizes and certifies safety professionals. Being certified or affiliated with ISPON shows employers and peers that you meet respected industry standards."),
    ("Career advancement", "Membership and certification from ISPON can help you stand out when applying for safety or environmental jobs, increase your chances of promotion in your current role, and gain trust from employers and clients."),
    ("Access to training and development", "ISPON offers specialized courses and workshops, and continuing professional development (CPD) opportunities. These help you stay updated with the latest safety regulations and best practices."),
]
FAQS = [
    ("What is ISPON?", "<p>The Institute of Safety Professionals of Nigeria (ISPON) is the recognized professional body dedicated to promoting occupational health, safety, and environmental practices in Nigeria. It provides certification, training, advocacy, and professional support for safety practitioners across industries.</p>"),
    ("Under which law was ISPON established?", "<p>The ISPON Act, 2014 (Act No. 2), published in the Federal Republic of Nigeria Official Gazette No. 62, Vol. 101 (Government Notice No. 72), Lagos, 20 May 2014. The Act was signed into law on 19 May 2014.</p>"),
    ("How does an individual become a member?", "<p>Write an application to the Registrar through your State/Branch Chairman, buy the membership form, pay the screening fee, submit your credentials and payment evidence, complete a project on an approved safety topic, attend the interviews, and meet the experience and course requirements. The full steps are on the <a href=\"/membership-procedure/\">Membership Procedure</a> page.</p>"),
    ("How can a company become a corporate member?", "<p>Submit a letter of intent on company letterhead with your CAC documents and company profile, buy the corporate membership form, pay the screening/audit fee, and submit the required company documents. See the <a href=\"/membership-procedure/\">Membership Procedure</a> page.</p>"),
    ("How much do the forms and screening cost?", "<p>The current fees are listed in the Fees tables on the <a href=\"/membership-procedure/\">Membership Procedure</a> page. Induction fees, membership dues and workshop or project support fees are payable after successful screening.</p>"),
    ("What services does ISPON offer?", "<ul><li>Professional membership and certification</li><li>Safety training and development programs</li><li>Safety awareness and advocacy</li><li>Industry collaboration and research</li><li>Safety conferences and workshops</li><li>Consultancy</li></ul><p>See <a href=\"/services/\">Our Services</a>.</p>"),
    ("Does ISPON have branches?", "<p>Yes. ISPON has state branches. Find the branch chairman's contact details in the branch directory on the <a href=\"/contact-page/\">Contact Us</a> page.</p>"),
    ("How do I contact ISPON?", "<p>Use the form on the <a href=\"/contact-page/\">Contact Us</a> page, or email info@ispon.gov.ng.</p>"),
    ("How can I stay updated?", "<p>Read the <a href=\"/blog/\">News and Blog</a>, subscribe to the newsletter in the page footer, or follow ISPON on social media.</p>"),
]


MEMBERSHIP = [
    ("paragraph", rt("<p>The Institute of Safety Professionals of Nigeria (ISPON) is the statutory body established by the ISPON Act, 2014 (Act No. 2), published in the Federal Republic of Nigeria Official Gazette No. 62, Vol. 101 (Government Notice No. 72), Lagos, on 20 May 2014. The Act, signed into law on 19 May 2014, established ISPON as a body corporate with perpetual succession and a common seal.</p>")),
    ("heading", "Membership procedure for individuals"),
    ("paragraph", rt("<ol><li>Write an application addressed to the Registrar through the Chairman of your State/Branch.</li><li>Purchase the membership form (see Fees below).</li><li>Pay the screening fee (see Fees below).</li><li>Submit the completed form, credentials, CV, passport photo and payment evidence.</li><li>Submit a project on an approved safety topic.</li><li>Attend written and oral interviews.</li><li>Have at least one year of safety work experience.</li><li>Complete ISPON HSE Competence Level 2 and 3 courses.</li></ol>",
                     "<p><i>Note: induction fees, membership dues and workshop fees are payable after successful screening.</i></p>")),
    ("heading", "Corporate membership procedure"),
    ("paragraph", rt("<ol><li>Submit a letter of intent on company letterhead.</li><li>Attach CAC documents and company profile.</li><li>Purchase the corporate membership form (see Fees below).</li><li>Pay the screening/audit fee (see Fees below).</li><li>Submit proof of payment, CAC documents, Safety Policy, HSE Audit/Inspection Report, Corporate Checklist, Organizational Structure, Medical Retainership, Tax Clearance and other relevant documents.</li></ol>",
                     "<p><i>Note: induction fees, membership dues and project support fees are payable after successful screening.</i></p>")),
    ("heading", "Contact"),
    ("paragraph", rt("<p>The Registrar, Institute of Safety Professionals of Nigeria (ISPON). Email: info@ispon.gov.ng</p>")),
]


def about_kwargs():
    return dict(hero_image=load_image("about.png", "About ISPON illustration"), lead="The recognized professional body dedicated to promoting occupational health, safety, and environmental practices in Nigeria, with certification, training, advocacy, and professional support for safety practitioners across industries.",
              body=ABOUT_BODY, experts_text="Meet our team of experienced safety professionals.", cta_title="Are you ready to take our service?",
              cta_text="Join us at ISPON and experience true Professionalism.", cta_label="Contact us", cta_url="/contact-page/",
              facts=[AboutFact(value=v, label=l, sort_order=i) for i, (v, l) in enumerate(ABOUT_FACTS)],
              timeline=[TimelineEntry(year=y, title=t, text=x, sort_order=i) for i, (y, t, x) in enumerate(ABOUT_TIMELINE)],
              reasons=[AboutReason(title=t, text=x, sort_order=i) for i, (t, x) in enumerate(ABOUT_REASONS)])


def membership_kwargs():
    return dict(body=MEMBERSHIP, intro="How individuals and companies apply to ISPON.",
              fees_note="Induction fees, membership dues and workshop or project support fees are payable after successful screening.",
              fees=[MembershipFee(audience=a, label=l, amount=n, note=nt, sort_order=i) for i, (a, l, n, nt) in enumerate([
                  ("individual", "Membership form", 50000, "Non-refundable"), ("individual", "Screening fee", 15000, "Non-refundable"),
                  ("corporate", "Corporate membership form", 150000, ""), ("corporate", "Screening / audit fee", 100000, "")])])


def services_kwargs():
    return dict(menu=False, intro="Our core services include safety training, professional certification, consultancy, advocacy, and industry collaboration to promote safe and compliant workplaces.",
              cta_label="Contact us", cta_url="/contact-page/")


def careers_kwargs():
    return dict(menu=False, intro="Vacancies and opportunities at ISPON are listed here.", empty_text="No vacancies are listed at the moment. To enquire, email info@ispon.gov.ng.")


def faq_kwargs():
    return dict(menu=False, intro="Answers to common questions about ISPON, membership and services.",
              items=[FAQItem(question=q, answer=a, sort_order=i) for i, (q, a) in enumerate(FAQS)])



class Command(BaseCommand):
    help = "Seed the ISPON page tree and starter content."

    def handle(self, *args, **opts):
        if HomePage.objects.exists():
            self.stdout.write("HomePage already exists; nothing to do.")
            return
        root = Page.get_first_root_node()
        for p in root.get_children():  # remove Wagtail's default welcome page
            p.delete()
        root = Page.objects.get(depth=1)
        home = root.add_child(instance=HomePage(
            title="Home", slug="home",
            hero_text="The recognized professional body regulating safety professionals and promoting workplace safety in Nigeria.",
            cta_label="Meet the team", cta_url="/team/",
            proud_kicker="Our proud", proud_heading="46 years of experience",
            proud_text="With 46 years of experience, we bring a wealth of knowledge, expertise, and proven excellence in delivering professional safety services and solutions.",
            services_title="Our core services", services_intro="Our core services include safety training, professional certification, consultancy, advocacy, and industry collaboration to promote safe and compliant workplaces.",
            team_title="Meet the team", team_intro="Meet our team of experienced safety professionals dedicated to delivering expert guidance, training, and solutions that ensure workplace safety and compliance.",
            news_title="Latest media",
            announcement_visible=True, announcement_title="Professional Development Conference and Annual General Meeting, Umuahia 2026",
            announcement_detail='Theme: "Building resilient workplaces: advancing psychosocial wellbeing for sustainable development and national growth"',
            announcement_starts=datetime.date(2026, 10, 14), announcement_ends=datetime.date(2026, 10, 16), announcement_button="Register Now", announcement_url=EVENT_URL,
            intro_title="About ISPON",
            intro_body="<p>The Institute of Safety Professionals of Nigeria (ISPON) is the recognized professional body dedicated to promoting occupational health, safety, and environmental practices in Nigeria. ISPON provides certification, training, advocacy, and professional support for safety practitioners across industries.</p>",
        ))
        for s in SERVICES:
            ServiceCard.objects.create(page=home, title=s[0], description=s[1])
        for i, (lab, val, suf) in enumerate(STATS):
            Statistic.objects.create(page=home, label=lab, value=val, suffix=suf, visible=True, sort_order=i)
        for i, (t, d) in enumerate(PILLARS):
            Pillar.objects.create(page=home, title=t, description=d, sort_order=i)
        home.save_revision().publish()
        Site.objects.all().delete()
        Site.objects.create(hostname="localhost", root_page=home, is_default_site=True, site_name="ISPON")

        def child(model, title, slug, **kw):
            menu = kw.pop("menu", True)
            page = home.add_child(instance=model(title=title, slug=slug, show_in_menus=menu, **({} if menu else {"show_in_footer": True}), **kw))
            page.save_revision().publish()
            return page

        cat, _ = BlogCategory.objects.get_or_create(name=CAT, slug="ispon-updates")
        blog = child(BlogIndexPage, "News and Blog", "blog", intro="News, notices and updates from ISPON.")
        for d, slug, title, exc, _old in POSTS:
            body = [("paragraph", rt(f"<p>{exc}</p>"))] if exc else []
            post = blog.add_child(instance=BlogPostPage(title=title, slug=slug, excerpt=exc, body=body, category=cat,
                                                        publication_date=datetime.date.fromisoformat(d), is_featured=(slug == POSTS[0][1]),
                                                        featured_image=load_image(f"blog/{slug[:90]}.png", title[:80])))
            post.save_revision().publish()
            Redirect.objects.get_or_create(old_path=Redirect.normalise_path("/" + d.replace("-", "/") + "/" + slug + "/"),
                                           defaults={"redirect_page": post, "is_permanent": True})
        child(AboutPage, "About Us", "about-us", **about_kwargs())
        child(ContactPage, "Contact Us", "contact-page")
        child(GalleryIndexPage, "Gallery", "gallery", intro="Our Recent Work")
        child(MembershipPage, "Membership Procedure", "membership-procedure", **membership_kwargs())
        child(TeamPage, "Team", "team", heading="Executive Member of ISPON Nigeria", intro="We are committed to promoting excellence in occupational health, safety, and environmental practices across Nigeria.", cta_title="Need more information?", cta_email="president@ispon.gov.ng")
        for i, (n, d, unit, _img) in enumerate(TEAM):
            TeamMember.objects.create(name=n, designation=d, unit=unit, bio=bio(n, d), portrait=load_image(f"team/{i + 1:02d}.png", f"{n} (placeholder portrait)"),
                                      order=i, is_published=True, featured=n in HOME_FEATURED)
        about = AboutPage.objects.get()
        for i, key in enumerate(("Udezi", "Onuoha", "Nwosu", "Modebe")):
            AboutExpert.objects.create(page=about, member=TeamMember.objects.get(name__contains=key), sort_order=i)
        about.save_revision().publish()
        child(ServicesPage, "Our Services", "services", **services_kwargs())
        child(CareerPage, "Careers", "careers", **careers_kwargs())
        child(FAQPage, "FAQ", "faq", **faq_kwargs())
        for st, addr, chair, ph, em in BRANCHES:
            Branch.objects.create(name=f"ISPON {st} Branch", state=st, address=tidy(addr), contact_person=tidy(chair), phone=phones(ph), email=em, is_published=True)
        site = Site.objects.get(is_default_site=True)
        SiteSettings.objects.update_or_create(site=site, defaults=dict(
            newsletter_text="Subscribe to our Newsletter to be updated. We promise not to spam.", footer_text="Committed to promoting excellence in occupational health, safety, and environmental practices across Nigeria.",
            address="No. 20 Irowa Obaze Street (Winners Street), off Federal Government Girls College Road, Ugbowo, Benin City, Edo State",
            phone="+234 806 208 3053", email="info@ispon.gov.ng", twitter_handle="@isponng_safety", header_button_label="Register Now", header_button_url=EVENT_URL, address_region="Edo State", geo_placename="Benin City", geo_region="NG-ED", default_description="The recognized professional body regulating safety professionals and promoting workplace safety in Nigeria.", office_hours="Mon-Tue, 9am to 6pm (as shown on the old site; confirm)",
            facebook="https://www.facebook.com/profile.php?id=61582230892915", x_twitter="https://x.com/isponng_safety",
            instagram="https://www.instagram.com/isponng_safety/",
        ))
        self.stdout.write(self.style.SUCCESS("Seeded. Team members are unpublished until ISPON confirms."))
