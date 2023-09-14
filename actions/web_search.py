""" Programatic internet searches """
from __future__ import annotations

import itertools

from duckduckgo_search import DDGS

from utils.log import get_logger

LOGGER = get_logger(__name__)
ddgs = DDGS()


def web_search(query: str, num_results: int = 4) -> list[str]:
    """
    Runs an internet search and returns the result list of urls.
    """
    LOGGER.info("Searching the internet with query: %s ...", query)
    results = []
    if query:
        results = list(itertools.islice(ddgs.text(query), num_results))
    urls = []
    for result in results:
        url = result.get("href")
        assert url, f"No href in search result: {result}"
        urls.append(url)
    return urls
