"""Utility functions for scraping https://github.com

Inspired by https://github.com/dogsheep/github-to-sqlite/pull/70
"""
import logging
import time
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse

import requests


def scrape_dependents(
    response: requests.Response, logger: Optional[logging.Logger] = None
) -> Iterable[Dict[str, Any]]:
    from bs4 import BeautifulSoup

    logger = logger or logging.getLogger("scraping")

    soup = BeautifulSoup(response.content, "html.parser")
    # Navigate through Package toggle if present
    base_url = urlparse(response.url).hostname or "github.com"
    options = soup.find_all("a", class_="select-menu-item")
    links = []
    if len(options) > 0:
        for link in options:
            links.append(link["href"])
    else:
        links.append(response.url)

    logger.debug(links)

    for link in links:
        yield from _scrape_dependents(f"https://{base_url}/{link}", logger)


def _scrape_dependents(url: str, logger: logging.Logger) -> Iterable[Dict[str, Any]]:
    # Optional dependency:
    from bs4 import BeautifulSoup, Tag

    s = requests.Session()

    while url:
        logger.debug(url)
        response = s.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        repo_names = [
            (a["href"] if not isinstance(a["href"], list) else a["href"][0]).lstrip("/")
            for a in soup.select("a[data-hovercard-type=repository]")
        ]
        stars = [
            int(s.next_sibling.strip())
            for s in soup.find_all("svg", {"class": "octicon octicon-star"})
        ]
        forks = [
            int(s.next_sibling.strip())
            for s in soup.find_all("svg", {"class": "octicon octicon-repo-forked"})
        ]

        if not len(repo_names) == len(stars) == len(forks):
            raise IndexError(
                "Could not find star and fork info. Maybe the GitHub page format has changed?"
            )

        repos = [
            {"name_with_owner": name, "stars": s, "forks": f}
            for name, s, f in zip(repo_names, stars, forks)
        ]

        logger.debug(repos)

        yield from repos

        # next page?
        try:
            next_link: Tag = soup.select(".paginate-container")[0].find_all(
                "a", text="Next"
            )[0]
        except IndexError:
            break
        if next_link is not None:
            href = next_link["href"]
            url = str(href if not isinstance(href, list) else href[0])
            time.sleep(1)
        else:
            url = ""
