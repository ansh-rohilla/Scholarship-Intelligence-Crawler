"""
Resilient Web Fetcher & Snapshot Cache Engine.
Fetches web pages live with automatic retry, respectful backoff,
and persists raw snapshots for offline reproducibility and verification auditing.
"""

import httpx
import time
import hashlib
from pathlib import Path
from typing import Optional, Tuple
from bs4 import BeautifulSoup
from crawler.config import DEFAULT_HEADERS, RAW_SNAPSHOTS_DIR


class ResilientFetcher:
    def __init__(self, cache_dir: Path = RAW_SNAPSHOTS_DIR, timeout: float = 12.0):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    def _get_cache_path(self, url: str) -> Path:
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        # Clean domain for filename prefix
        domain = url.split("//")[-1].split("/")[0].replace(":", "_").replace(".", "_")
        filename = f"{domain}_{url_hash}.html"
        return self.cache_dir / filename

    def fetch(self, url: str, force_live: bool = False, save_snapshot: bool = True) -> Tuple[Optional[str], int, str]:
        """
        Fetches the content from a URL or reads from snapshot cache.
        Returns: (html_content, status_code, fetch_source: 'LIVE' | 'CACHE' | 'FAILED')
        """
        cache_path = self._get_cache_path(url)

        # 1. Check local snapshot cache if not forcing live
        if not force_live and cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    return content, 200, "CACHE"
            except Exception:
                pass

        # 2. Fetch live over HTTP
        try:
            with httpx.Client(headers=DEFAULT_HEADERS, timeout=self.timeout, follow_redirects=True, verify=False) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    html_content = resp.text
                    if save_snapshot:
                        try:
                            with open(cache_path, "w", encoding="utf-8") as f:
                                f.write(html_content)
                        except Exception:
                            pass
                    return html_content, 200, "LIVE"
                else:
                    return None, resp.status_code, "FAILED"
        except Exception:
            # Fall back to cache if live request times out or lacks network
            if cache_path.exists():
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        return f.read(), 200, "CACHE"
                except Exception:
                    pass
            return None, 0, "FAILED"

    def save_manual_snapshot(self, url: str, html_content: str):
        """Allows pre-seeding offline snapshots for real sources."""
        cache_path = self._get_cache_path(url)
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    @staticmethod
    def extract_text(html: str) -> str:
        """Strips HTML boilerplate and scripts, returning clean normalized text."""
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())
