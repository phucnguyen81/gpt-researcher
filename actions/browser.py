""" Scraper code goes here """
from contextlib import contextmanager

from playwright.sync_api import sync_playwright, Page, Browser


@contextmanager
def browser_page(headless=True):
    """ Get a browser page context """
    with sync_playwright() as context:
        browser: Browser = context.chromium.launch(headless=headless)
        page: Page = browser.new_page()
        try:
            yield page
        finally:
            browser.close()
