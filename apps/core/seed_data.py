"""Starter content copied from ispon.gov.ng. Plain data, no Django imports (also used by the asset generator)."""
OLD = "https://ispon.gov.ng/wp-content/uploads/"
LOGO_URL = OLD + "2026/03/cropped-Untitled-design-6-scaled-1.png"
EVENT_URL = "https://isponconf-2026.org/"

# (date, slug as on the old site, title, excerpt, old featured image path or "")
POSTS = [
    ("2026-09-18", "expanding-the-safety-vanguard-highlights-from-the-ispon-abia-state-branch-induction-ceremony", "Expanding the Safety Vanguard: Highlights from the ISPON Abia State Branch Induction Ceremony", "", ""),
    ("2026-08-05", "live-television-engagement-at-edo-state-broadcasting-services-ebs-benin", "Live television engagement at Edo State broadcasting services (EBS BENIN)", "Photos from today's visit and live television engagement at Edo State broadcasting services (EBS BENIN) by ISPON President Chief Dr Udezi Stephen, ISPON Edo state branch Chairman Mr Ben Itakiri and the Institute's deputy Registrar Mrs Joy Agbroko.", ""),
    ("2026-07-28", "safety-experts-demand-curriculum-reform-in-schools", "Safety experts demand curriculum reform in schools", "", ""),
    ("2026-07-22", "abia-government-teams-up-with-ispon-to-enforce-safety-standards", "Abia Government Teams Up With ISPON To Enforce Safety Standards", "LAGOS: The Abia State Government has pledged to strengthen workplace and public safety through a new partnership with the Institute of Safety Professionals of Nigeria (ISPON) as part of its broader industrialisation agenda.", "2026/07/abia-ispon.jpg"),
    ("2026-05-26", "enhancing-workplace-safety-in-nigeria-with-chief-dr-stephen-udezi-l-a", "Enhancing Workplace Safety in Nigeria with Chief Dr. Stephen Udezi L.A", "Watch the interview.", "2026/05/428524-768x768.jpg"),
    ("2026-05-26", "ispon-renews-call-for-stronger-national-safety-reforms", "ISPON Renews Call for stronger National Safety Reforms", "ISPON President, Dr. Stephen Udezi, who addressed a press conference on Friday ahead of the anniversary, which will be held in Warri, Delta State, stressed the need for a cultural shift towards safety prevention.", "2026/05/428515.jpg"),
    ("2026-05-26", "more-advocacy-for-safety-in-nigeria-from-chief-dr-udezi-stephen-ispon-president-at-the-press-briefing-in-lagos-to-mark-the-12-years-anniversary-of-the-ispon-act-2014", "More advocacy for safety in Nigeria from Chief Dr Udezi Stephen, ISPON President, at the press briefing in Lagos to mark the 12 year's anniversary of the ISPON Act 2014", "", ""),
    ("2026-05-12", "membership-procedure", "Membership Procedure", "The Institute of Safety Professionals of Nigeria (ISPON) Act, 2014 (Act No. 2) published in the Federal Republic of Nigeria Official Gazette No 62, Vol 101 (Government Notice No. 72), Lagos, 20th May, 2014.", ""),
    ("2026-05-10", "to-whom-it-may-concern", "To Whom It May Concern", "The Institute of Safety Professionals of Nigeria (ISPON) Act, 2014 (Act No. 2) published in the Federal Republic of Nigeria Official Gazette No 62, Vol 101 (Government Notice No. 72), Lagos, 20th May, 2014.", ""),
    ("2026-05-02", "ispon-public-notice-on-leadership-official-statement-on-misrepresentation-and-court-ruling-2026", "ISPON Public Notice on Leadership: Official Statement on Misrepresentation and Court Ruling (2026)", "Published: April 27, 2026. ISPON has issued an official public notice to address ongoing concerns regarding the misrepresentation of its leadership and unauthorized claims made by certain individuals.", "2026/03/198484-768x998.jpg"),
    ("2026-03-20", "ispon-anambra-state-branch-is-a-goal", "ISPON Anambra State Branch Is a Goal!", "ISPON President Chief Dr Udezi Stephen, the Deputy Registrar and Electoral Committee Chairman, had a successful Induction of New Members, Re-inauguration of ISPON Anambra State Branch and Election of State Executives on 14 February 2026 at Awka.", ""),
    ("2026-03-04", "presentation-of-safety-ambassador-award-to-his-excellency-the-governor-of-kogi-state-alhaji-usman-ahmed-ododo-by-the-president-of-institute-of-safety-professionals-of-nigeria-chief-dr-udezi-stephen-a", "Presentation of Safety Ambassador Award to His Excellency the Governor of Kogi State", "Presentation of the Safety Ambassador Award to His Excellency the Governor of Kogi State, Alhaji Usman Ahmed Ododo, by the ISPON President, Chief Dr. Udezi Stephen, at Government House, Kogi State, on 27 January 2026.", ""),
]

# (name, designation, unit, portrait image path on the old site). Order and spelling as on ispon.gov.ng/team/ (Nwosu confirmed by ISPON).
TEAM = [
    ("Chief Dr. Udezi Stephen Lucky Awore", "President", "Executive", "2026/02/23-scaled.png"),
    ("Dr. Foreman Chido Onuoha", "Deputy President", "Executive", "2026/02/28-scaled.png"),
    ("Mazi Harold Uzor Echendu", "Governing Board Member", "Governing Board", "2026/02/35-1-scaled.png"),
    ("Bidr. Julius E. Okoh", "Governing Board Member", "Governing Board", "2026/02/29-scaled.png"),
    ("Dr. (Mrs.) Monica Nwosu", "Governing Board Member", "Governing Board", "2026/02/33-scaled.png"),
    ("Dr. Francis Iwu", "Governing Board Member", "Governing Board", "2026/02/24-scaled.png"),
    ("Dr. Lucky Oderhohwo", "Governing Board Member", "Governing Board", "2026/02/27-scaled.png"),
    ("Dr. Obele Realman Evans", "Governing Board Member", "Governing Board", "2026/02/34-1-scaled.png"),
    ("Dr. Tesh M. Kibikiwa", "Governing Board Member", "Governing Board", "2026/02/26-scaled.png"),
    ("Mr. Akpan Ottobong Etim", "Governing Board Member", "Governing Board", "2026/02/22-scaled.png"),
    ("Mrs. Ajayi Ibironke", "Governing Board Member", "Governing Board", "2026/02/31-scaled.png"),
    ("Mr Benjamin Modebe", "Registrar", "Registry", "2026/02/30-scaled.png"),
    ("Mr. Gilbert Ikedimma", "Governing Board Member", "Governing Board", "2026/02/32-scaled.png"),
    ("Adm. (Mrs.) Joy Agbroko", "Deputy Registrar", "Registry", "2026/02/25-scaled.png"),
]
GALLERY_PHOTOS = [OLD + p for p in (
    "2026/07/DSC_0472-scaled.jpg", "2026/07/DSC_0473-scaled.jpg", "2026/07/DSC_0475-scaled.jpg", "2026/07/DSC_0477-scaled.jpg",
    "2026/07/abia-ispon-2.jpg", "2026/07/abia-2.jpg", "2026/02/IMG-20260128-WA0008.jpg", "2026/02/IMG-20260128-WA0007.jpg",
    "2026/02/IMG-20260128-WA0005.jpg", "2026/02/IMG-20260128-WA0004-1.jpg")]


def initials(name):
    skip = {"chief", "dr.", "dr", "mrs.", "mrs", "mr.", "mr", "mazi", "bidr.", "adm.", "(mrs.)"}
    parts = [p for p in name.split() if p.lower() not in skip]
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else parts[0][:2].upper()


def bio(name, designation):
    return f"<p>{name} serves as {designation} of the Institute of Safety Professionals of Nigeria (ISPON).</p>"
