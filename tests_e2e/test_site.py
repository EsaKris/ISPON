"""Browser tests (Playwright). NOT yet executed: the build sandbox could not download a browser.
Run locally:  pip install -r requirements-dev.txt && playwright install chromium
              python manage.py migrate && python manage.py seed_site   (with DJANGO_DEBUG=1)
              DJANGO_DEBUG=1 python manage.py runserver &  then  pytest tests_e2e
"""
import os

import pytest
from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("E2E_BASE", "http://localhost:8000")
PATHS = ["/", "/blog/", "/about-us/", "/contact-page/", "/gallery/", "/membership-procedure/", "/team/"]


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.mark.parametrize("size", [(1440, 900), (390, 844)], ids=["desktop", "mobile"])
@pytest.mark.parametrize("path", PATHS)
def test_pages_render_without_horizontal_scroll_or_console_errors(browser, path, size):
    page = browser.new_page(viewport={"width": size[0], "height": size[1]})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    assert page.goto(BASE + path).status == 200
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    assert not errors


def test_mobile_menu_opens_with_keyboard(browser):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.goto(BASE + "/")
    btn = page.get_by_role("button", name="Menu")
    btn.focus()
    page.keyboard.press("Enter")
    expect(page.locator("#nav")).to_be_visible()


def test_gallery_wall_lightbox_keyboard(browser):
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto(BASE + "/gallery/")
    page.locator(".tile").first.focus()
    page.keyboard.press("Enter")
    expect(page.locator("#lb.on")).to_be_visible()
    page.keyboard.press("ArrowRight")
    page.keyboard.press("Escape")
    expect(page.locator("#lb.on")).to_have_count(0)


def test_team_badge_flips(browser):
    page = browser.new_page()
    page.goto(BASE + "/team/")
    flips = page.locator(".flip")
    if flips.count():  # team records are seeded unpublished until ISPON confirms
        flips.first.click()
        expect(flips.first).to_have_attribute("aria-pressed", "true")


def test_contact_form_shows_errors(browser):
    page = browser.new_page()
    page.goto(BASE + "/contact-page/")
    page.get_by_label("Email").fill("not-an-email")
    page.get_by_role("button", name="Send message").click()
    assert page.locator("input:invalid").count() >= 1
