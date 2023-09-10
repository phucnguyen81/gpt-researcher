""" Scraper code goes here """
from contextlib import asynccontextmanager

from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright


@asynccontextmanager
async def browser_page(headless=True):
    """ Get a browser page context """
    with await async_playwright() as context:
        browser = await context.chromium.launch(headless=headless)
        page = await browser.new_page()
        try:
            yield page
        finally:
            await browser.close()
