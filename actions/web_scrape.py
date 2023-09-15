"""Selenium web scraping module."""
from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from config import Config
from utils.log import get_logger
from processing.text import summarize_text

LOGGER = get_logger(__name__)
FILE_DIR = Path(__file__).parent.parent
CFG = Config()


def summarize_page(url: str, question: str, page) -> str:
    """Browse a website and return the answer and links to the user

    Args:
        url (str): The url of the website to browse
        question (str): The question asked by the user
        page (Page): The browser Page object

    Returns:
        str: The answer and links to the user
    """
    LOGGER.info("Browsing the %s for relevant about: %s...", url, question)
    try:
        text = scrape_text_with_selenium(page, url)
        LOGGER.debug("Text scraped from url %s: %s", url, text)
        add_header(page)
        summary_text = summarize_text(text, question, page)

        LOGGER.info("Information gathered from url %s: %s", url, summary_text)
        return f"Information gathered from url {url}: {summary_text}"
    except Exception as error:
        LOGGER.error(
            "An error occurred while processing the url %s: %s", url, error
        )
        return f"Error processing the url {url}: {error}"


def scrape_text_with_selenium(page, url: str) -> str:
    """Scrape text from a website using selenium
    Args:
        url (str): The url of the website to scrape
    Returns:
        str: the text scraped from the website
    """
    page.goto(url)
    # Get the HTML content directly from the browser's DOM
    page_source = page.content()
    soup = BeautifulSoup(page_source, "html.parser")

    for script in soup(["script", "style"]):
        script.extract()

    # text = soup.get_text()
    text = get_text(soup)

    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = "\n".join(chunk for chunk in chunks if chunk)
    return text


def get_text(tag):
    """ Get the significant text from a tag. The significant text is the text
    from headings and paragraphs.
    Args:
        tag (Tag): The tag to get the text from
    Returns:
        str: The significant text from the tag
    """
    text = ""
    tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'p']
    for element in tag.find_all(tags):
        text += element.text + "\n\n"
    return text


def add_header(page) -> None:
    """Add a header to the website. The header shows an overlay over the page
    telling the user that the page is being processed.
    """
    with open(f"{FILE_DIR}/js/overlay.js", "r", encoding="utf-8") as jsfile:
        page.evaluate(jsfile.read())


def main(url: str, question: str):
    """Run the selenium web scraping module."""
    # pylint: disable=import-outside-toplevel
    from playwright.sync_api import sync_playwright

    with sync_playwright() as context:
        browser = context.chromium.launch(headless=False)
        page = browser.new_page()
        try:
            summarize_page(url, question, page)
        finally:
            page.close()
            browser.close()


if __name__ == "__main__":
    main(
        url="https://www.pcmag.com/brands/openai",
        question="OpenAI applications and features",
    )
