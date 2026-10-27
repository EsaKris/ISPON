# CMS guide for staff
Sign in at `/admin/`. The dashboard opens with **Quick actions** (write an article, create an album, upload photos, edit membership fees, add a team member or branch).
Left menu: **News**, **Photo albums**, **Upload photos**, **People & contacts** (team, branches, contact messages, newsletter subscribers), Pages, Images, Documents, Settings.

- **News articles (including the ones already loaded):** News menu (or Pages > News and Blog) > click an article > edit the text, image, date, category, tags > Publish. "Save draft" keeps it private. Use "Schedule" (Publishing options) to go live later. Old articles only hold the excerpt, so paste the full text into the body.
- **Membership fees:** Pages > Membership Procedure > Fees section. Each fee is one row (individual or corporate, label, amount in naira, note). Change the amount, untick "visible" to hide a row, or add a row, then Publish. Set "fees confirmed" to show the date. The step-by-step text is edited in the same page's body.
- **Photos:** (1) Photo albums > create an album (or Pages > Gallery > add child page "Album page"). (2) **Upload photos** > choose the album > select up to 30 photos at once > Upload. Identical files are not stored twice. (3) Open the album to add captions, alt text, credits, reorder by dragging, or untick "published" on a photo to hide it. Published albums appear on the wall and the Albums list automatically.
- **Homepage:** click **Homepage** at the top of the left menu (or the Edit the homepage quick action). Tabs: Hero and event (headline, buttons, upcoming-event banner), About and highlights (intro text and the five highlights that also scroll in the yellow band), Our proud and numbers (the "46 years" text and the numbers such as 12,000+ registered professionals), Services (heading, intro and the six cards), Team and news headings. Tick or untick "visible" on any number, highlight or card to show or hide it. Top-bar phone and email, the menu button (for example Register Now) and the newsletter sentence are in Settings > Site settings.
- **Team:** People & contacts > Team members. "Published" shows a person; "featured" puts them on the homepage; "former member" archives them; lower order numbers come first.
- **Branches:** People & contacts > Branches. Tick "published" and it appears on Contact Us.
- **About and other text pages:** Pages > edit. Blocks: heading, paragraph, image, button, document, FAQ; drag to reorder.
- **Contact messages and subscribers:** People & contacts (only roles with permission see them).
- **Contact details, social links, logo:** Settings > Site settings. **Redirects:** Settings > Redirects.
- **Roles:** Content Administrator (all pages and media), Gallery Manager (Gallery pages and media), Branch & Team Manager (branches, team, media). None can manage users.

## Logo, sharing pictures and SEO
- **Logo:** Settings > Site settings > Logo. One upload sets the website header, footer, browser-tab icon, phone home-screen icon, the admin menu and login logo, the structured data used by Google, and the fallback picture for shared links. Use a square PNG with a transparent background, at least 512 x 512.
- **Picture shown when a link is shared:** for a news article it is the article's featured image. For other pages use Promote > Social image. If none is set, the Default share image in Site settings is used, then the logo. Use 1200 x 630 pictures for the best result.
- **Page title and description for Google:** on any page, Promote tab > "Title tag" and "Meta description" (aim for 50-60 and 120-155 characters).
- **Site settings > Search and sharing:** default description, default share image, Google Search Console and Bing verification tokens.
- **Site settings > Location (geo tags):** city, state, ISO region code and the head office latitude and longitude. Coordinates are only published when you enter them.
- **Needed once at go-live:** Settings > Sites: set the hostname to `ispon.gov.ng`, otherwise links in the page code, the sitemap and the news feed use the wrong address.

## Newsletter
- Visitors subscribe in the footer. They get an email with a confirmation link and only start receiving newsletters after confirming. People who never confirm are never emailed.
- **Write one:** People & contacts > Newsletters > Add. **Check it:** Send newsletters (left menu) > "Send me a test" (uses the email address on your account). **Send it:** "Queue to send". It goes out in batches within minutes, depending on the scheduled job. "Pause" holds the unsent part.
- The table shows confirmed subscribers, sent, failed and waiting counts. Failed means the mail server refused the address or was unavailable.
- Every email has an unsubscribe link. People who unsubscribe are never emailed again unless they subscribe and confirm again.
- Subscribers are listed under People & contacts > Subscribers (confirmed date, active or not). Only the Newsletter Manager role and administrators can see them.

## Team page
People & contacts > Team members: name, designation, unit, portrait, biography, order. The text above the badges ("Executive Member of ISPON Nigeria"), the intro and the "Need more information?" box are on Pages > Team.

## About, Services, FAQ and Careers
- **About Us** (Pages > About Us): the opening statement, history text, key facts, timeline entries, "why choose us" cards, the experts (pick people from Team members) and the closing call to action. Everything is a field or a row you can add, edit, reorder or delete.
- **Our Services:** shows the service cards you manage on Home > Services, plus its own intro text and button.
- **FAQ:** add, edit, reorder or hide questions (untick "visible"). Google can show them in search results.
- **Careers:** add a Vacancy (title, place, description, apply email or link, closing date). With none visible, the page shows the "no vacancies" message you can edit.
- These three pages appear in the footer, not the main menu. To change that, open the page > Promote tab > "Show in footer".

## Page top bands and the About picture
Every page opens with the same dark band (small label, big title and an optional lead sentence). The lead comes from the page's intro field. On Pages > About Us, the **Hero picture** field sets the picture on the right of the band on desktop (760 x 600 works well; phones hide it). It currently holds a generated illustration: replace it with a real ISPON photo.

## Homepage hero: slides, pictures and videos
Pages > Home > **Hero and event** tab > **Hero slides**. Add as many slides as you like; with two or more, the hero becomes a carousel (arrows, dots, a pause button, swipe, and arrow keys; it pauses when someone hovers or focuses it, and never auto-plays for people who prefer reduced motion).
- **Style: Signature design** keeps the dark hero where moving the cursor lights up hidden hazards.
- **Style: Your picture**: choose an image (wide, about 1920 x 900). A dark gradient is added so the text stays readable.
- **Style: Your video**: upload an MP4 or WebM under Documents (short, muted, ideally under 8 MB; it loops and starts by itself) and choose it, or paste a direct video link. Add a Poster picture, which shows while it loads.
- Each slide has its own small label, headline (one line per row), text and up to two buttons. Untick "visible" to hide a slide. "Seconds per slide" and "Slides change automatically" are at the top of the section. With no slides, the simple fields under "Fallback hero" are used.
- The **numbers** (12,000+, 46+, 2,930) count up when they scroll into view; edit them on the "Our proud and numbers" tab.

## Event banner and countdown
Home > Hero and event > Upcoming event banner. When the start date is in the future, a live countdown (days, hours, minutes, seconds, counting to 08:00 on the start date) appears in the banner automatically. After the end date the banner is labelled "Past event" and the button and countdown disappear. Untick "visible" to hide the banner.

## Signing in securely
- Your password must be 14+ characters and not a common one. Use a password manager.
- The first time you sign in you must set up **two-factor authentication**: scan the QR code with an authenticator app (Google Authenticator, Microsoft Authenticator, Authy...) and keep the backup codes somewhere safe and offline. After that you enter a 6-digit code at each sign-in.
- After 5 wrong attempts your account is locked for an hour. Never share your login; the site signs you out after 2 hours of inactivity.
- Lost your phone? Ask an administrator to reset your two-factor device (Settings > Users).
- **Legal pages:** Pages > Privacy Policy, Cookie Policy, Terms of Use are normal pages. If you change how the website collects data (new forms, analytics, a mailing service), update them first.
- **Contact messages and subscribers** are deleted automatically on a schedule (24 months, 12 months, 30 days). Do not copy them into spreadsheets or chats.
