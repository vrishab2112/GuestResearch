import os
from typing import List, Dict, Optional
import requests


TAVILY_ENDPOINT = "https://api.tavily.com/search"
# Fallback default provided by user (env var overrides it)
DEFAULT_TAVILY_KEY = "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"


class TavilyClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY") or DEFAULT_TAVILY_KEY
        self.session = requests.Session()

    def _search(self, query: str, max_results: int = 10, depth: str = "advanced") -> List[Dict]:
        if not self.api_key:
            return []
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": depth,
            "max_results": max_results,
        }
        try:
            r = self.session.post(TAVILY_ENDPOINT, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            results = data.get("results", [])
            normalized: List[Dict] = []
            for res in results:
                normalized.append({
                    "title": res.get("title"),
                    "url": res.get("url"),
                    "content": res.get("content"),
                    "source_type": "tavily_result",
                })
            return normalized
        except Exception:
            return []

    def search_overview(self, guest: str, max_results: int = 8) -> List[Dict]:
        return self._search(f"{guest} biography profile background", max_results=max_results)

    def search_books_and_articles(self, guest: str, max_results: int = 12) -> List[Dict]:
        # Articles about guest and books by/about guest
        return self._search(f"{guest} books articles interviews bibliography publications", max_results=max_results)

    def search_social_handles(self, guest: str, max_results: int = 10) -> List[Dict]:
        results = self._search(f"{guest} official social media links Twitter X Instagram LinkedIn Facebook", max_results=max_results)
        # Keep likely social domains
        keep_domains = ("twitter.com", "x.com", "instagram.com", "linkedin.com", "facebook.com", "threads.net", "tiktok.com", "youtube.com")
        filtered = [r for r in results if any(d in (r.get("url") or "") for d in keep_domains)]
        return filtered or results


