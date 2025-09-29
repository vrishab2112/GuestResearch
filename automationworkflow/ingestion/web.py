from typing import List, Dict
from urllib.parse import urlencode, urlparse, parse_qs, unquote
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


class WebIngestor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        })

    def _normalize_ddg_link(self, href: str) -> str:
        # DuckDuckGo wraps outbound links through /l/?uddg=ENCODED
        if href.startswith("//"):
            href = "https:" + href
        parsed = urlparse(href)
        if (parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/") and "uddg" in parse_qs(parsed.query)):
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            return unquote(target)
        return href

    def search_ddg(self, query: str, max_results: int = 10) -> List[str]:
        # DuckDuckGo lite HTML search
        params = {"q": query}
        url = f"https://duckduckgo.com/html/?{urlencode(params)}"
        try:
            r = self.session.get(url, timeout=30)
            r.raise_for_status()
        except Exception:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        links: List[str] = []
        seen = set()
        for a in soup.select("a.result__a"):
            href = a.get("href")
            if not href:
                continue
            # Skip YouTube domains for non-YT web ingestion
            href = self._normalize_ddg_link(href)
            if re.search(r"youtube\.com|youtu\.be", href):
                continue
            if href in seen:
                continue
            seen.add(href)
            links.append(href)
            if len(links) >= max_results:
                break
        return links

    def search_bing(self, query: str, max_results: int = 10) -> List[str]:
        params = {"q": query}
        url = f"https://www.bing.com/search?{urlencode(params)}"
        try:
            r = self.session.get(url, timeout=30)
            r.raise_for_status()
        except Exception:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        links: List[str] = []
        seen = set()
        for a in soup.select("li.b_algo h2 a, h2 a"):  # tolerant selector
            href = a.get("href")
            if not href:
                continue
            if re.search(r"youtube\.com|youtu\.be", href):
                continue
            if href in seen:
                continue
            seen.add(href)
            links.append(href)
            if len(links) >= max_results:
                break
        return links

    def search(self, query: str, max_results: int = 10) -> List[str]:
        links = self.search_ddg(query, max_results=max_results)
        if not links:
            links = self.search_bing(query, max_results=max_results)
        return links

    def search_links(self, query: str, site_filter: str = "", max_results: int = 10) -> List[str]:
        q = f"{query} {site_filter}".strip()
        return self.search(q, max_results=max_results)

    def fetch_url(self, url: str) -> Dict:
        r = self.session.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # Drop common noise blocks
        for sel in [
            "header", "nav", "footer", "aside", "form",
            "div[class*='header']", "div[class*='nav']", "div[id*='nav']",
            "div[class*='subscribe']", "div[class*='signup']",
        ]:
            for el in soup.select(sel):
                el.decompose()
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()
        # Prefer main/article if present
        main = soup.select_one("main") or soup.select_one("article") or soup
        paragraphs = [p.get_text(" ", strip=True) for p in main.select("p")]
        body_text = " ".join([p for p in paragraphs if p])
        if not body_text:
            body_text = main.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", (body_text or "").strip())
        title = soup.title.string.strip() if soup.title and soup.title.string else url
        return {
            "source_type": "web_article",
            "url": url,
            "title": title,
            "text": text,
            "fetched_at": datetime.utcnow().isoformat(),
        }

    def safe_fetch(self, url: str) -> Dict:
        try:
            return self.fetch_url(url)
        except Exception:
            return {
                "source_type": "web_link",
                "url": url,
                "title": url,
                "text": "",
                "fetched_at": datetime.utcnow().isoformat(),
            }

    def search_and_fetch(self, query: str, max_results: int = 10) -> List[Dict]:
        urls = self.search(query, max_results=max_results)
        results: List[Dict] = []
        for u in urls:
            results.append(self.safe_fetch(u))
        return results

    def categorized_discovery(self, guest: str) -> Dict[str, List[str]]:
        """Return categorized link lists without fetching pages."""
        out: Dict[str, List[str]] = {
            "wikipedia": [],
            "blogs": [],
            "books": [],
            "personal": [],
            "news": [],
            "social": [],
            "podcasts": [],
        }
        # Wikipedia (prefer English Wikipedia)
        out["wikipedia"] = self.search_links(f"{guest}", site_filter="site:en.wikipedia.org", max_results=3)
        # Blogs (medium, substack, dev blogs)
        blogs = []
        blogs += self.search_links(f"{guest}", site_filter="site:medium.com", max_results=5)
        blogs += self.search_links(f"{guest}", site_filter="site:substack.com", max_results=5)
        blogs += self.search_links(f"{guest} blog", max_results=5)
        # Personal website (heuristic: first non-social domain from 'official site' query)
        personal = self.search_links(f"{guest} official site", max_results=5)
        # Books
        books = []
        books += self.search_links(f"{guest} books site:books.google.com", max_results=5)
        books += self.search_links(f"{guest} books site:goodreads.com", max_results=5)
        books += self.search_links(f"{guest} author site:amazon.com", max_results=5)
        # News / interviews
        news = []
        news += self.search_links(f"{guest} interview", max_results=5)
        news += self.search_links(f"{guest} site:nytimes.com", max_results=3)
        news += self.search_links(f"{guest} site:theguardian.com", max_results=3)
        news += self.search_links(f"{guest} site:espncricinfo.com", max_results=3)
        # Social / bio
        social = []
        social += self.search_links(f"{guest} LinkedIn", max_results=3)
        social += self.search_links(f"{guest} Twitter", max_results=3)
        social += self.search_links(f"{guest} X.com", max_results=3)
        social += self.search_links(f"{guest} biography", max_results=5)
        # Podcasts
        podcasts = []
        podcasts += self.search_links(f"{guest} podcast site:open.spotify.com", max_results=5)
        podcasts += self.search_links(f"{guest} podcast site:podcasts.apple.com", max_results=5)
        podcasts += self.search_links(f"{guest} podcast site:podchaser.com", max_results=5)
        out["blogs"] = list(dict.fromkeys(blogs))
        out["personal"] = list(dict.fromkeys(personal))
        out["books"] = list(dict.fromkeys(books))
        out["news"] = list(dict.fromkeys(news))
        out["social"] = list(dict.fromkeys(social))
        out["podcasts"] = list(dict.fromkeys(podcasts))
        return out

    def fetch_from_categories(self, categories: Dict[str, List[str]], per_category_fetch: int = 3) -> List[Dict]:
        results: List[Dict] = []
        for cat, links in categories.items():
            if not isinstance(links, list) or not links:
                continue
            fetched = 0
            for u in links:
                rec = self.safe_fetch(u)
                results.append(rec)
                fetched += 1
                if fetched >= per_category_fetch:
                    break
        return results


