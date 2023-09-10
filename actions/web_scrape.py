"""Selenium web scraping module."""
from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from config import Config
from log.log import get_logger
import processing.text as summary

LOGGER = get_logger(__name__)
FILE_DIR = Path(__file__).parent.parent
CFG = Config()


def sync_browse(url: str, question: str, page) -> str:
    """Browse a website and return the answer and links to the user

    Args:
        url (str): The url of the website to browse
        question (str): The question asked by the user

    Returns:
        str: The answer and links to the user
    """
    LOGGER.info("Browsing the %s for relevant about: %s...", url, question)
    try:
        text = scrape_text_with_selenium(page, url)
        add_header(page)
        summary_text = summary.summarize_text(url, text, question, page)

        LOGGER.info("📝 Information gathered from url %s: %s", url, summary_text)
        return f"Information gathered from url {url}: {summary_text}"
    except Exception as error:
        LOGGER.error("An error occurred while processing the url %s: %s", url, error)
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


def get_text(soup):
    """Get the text from the soup

    Args:
        soup (BeautifulSoup): The soup to get the text from

    Returns:
        str: The text from the soup
    """
    text = ""
    tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'p']
    for element in soup.find_all(tags):  # Find all the <p> elements
        text += element.text + "\n\n"
    return text


def add_header(page) -> None:
    """Add a header to the website
    """
    with open(f"{FILE_DIR}/js/overlay.js", "r", encoding="utf-8") as jsfile:
        page.evaluate(jsfile.read())
