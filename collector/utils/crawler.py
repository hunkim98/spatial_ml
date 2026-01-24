import re
import time
import requests
from bs4 import BeautifulSoup, Tag


class CrawlerUtil:
    @staticmethod
    def is_heading(tag: Tag) -> bool:
        return (
            isinstance(tag, Tag)
            and tag.name in {"h1", "h2", "h3", "h4"}
            and tag.get_text(strip=True)
        )

    @staticmethod
    def norm(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "")).strip().lower()

    @staticmethod
    def fetch_html(url, max_retries: int = 3, timeout: int = 20, headers=None) -> str:
        last_err = None
        session = requests.Session()
        if headers:
            session.headers.update(headers)
        else:
            session.headers.update(
                {
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    )
                }
            )
        for i in range(max_retries):
            try:
                resp = session.get(url, timeout=timeout)
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                last_err = e
                time.sleep(0.8 * (i + 1))
        raise RuntimeError(f"Failed to fetch {url}") from last_err

    @staticmethod
    def crawl(url: str, max_retries: int = 3, timeout: int = 20, headers=None):
        """
        Fetches the content at the given URL and parses it with BeautifulSoup.

        Args:
            url (str): The URL to crawl.

        Returns:
            BeautifulSoup: Parsed HTML content of the page.
        """
        try:
            html = CrawlerUtil.fetch_html(
                url, max_retries=max_retries, timeout=timeout, headers=headers
            )
            soup = BeautifulSoup(html, "html.parser")
            return soup
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return None
