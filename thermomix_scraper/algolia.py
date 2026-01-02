"""Algolia search client for recipe discovery."""

from __future__ import annotations

import json
import logging
from collections import deque
from typing import TYPE_CHECKING, Generator
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from selenium.webdriver.chrome.webdriver import WebDriver

    from .config import Config

log = logging.getLogger("thermomix.algolia")


class AlgoliaClient:
    """Client for Cookidoo's Algolia search backend."""
    
    # Characters for prefix-based discovery
    SEARCH_CHARS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜabcdefghijklmnopqrstuvwxyzäöü0123456789")
    MAX_DEPTH = 3
    HITS_PER_PAGE = 1000
    
    def __init__(self, config: Config):
        self.config = config
        self.endpoint: str | None = None
        self.app_id: str | None = None
        self.api_key: str | None = None
        self.lang_filter: str | None = None
    
    def initialize(self, driver: WebDriver) -> None:
        """Initialize Algolia config from the search page."""
        search_url = f"{self.config.base_url}search/"
        driver.get(search_url)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        next_data = soup.select_one("script#__NEXT_DATA__")
        
        if not next_data or not next_data.string:
            raise RuntimeError("Missing __NEXT_DATA__ on search page")
        
        data = json.loads(next_data.string)
        props = (data.get("props") or {}).get("pageProps") or {}
        
        self.app_id = props.get("algoliaAppId")
        api_key_data = props.get("algoliaApiKeyData") or {}
        self.api_key = api_key_data.get("apiKey")
        
        indices = props.get("algoliaIndices") or {}
        recipes = indices.get("recipes") or {}
        index_name = recipes.get("title") or recipes.get("relevance_empty") or recipes.get("relevance")
        
        if not all([self.app_id, self.api_key, index_name]):
            raise RuntimeError("Incomplete Algolia configuration")
        
        self.endpoint = f"https://{self.app_id}-dsn.algolia.net/1/indexes/{index_name}/query"
        
        lang_code = self.config.locale.split("-")[0]
        self.lang_filter = f"language:{lang_code}"
        
        log.info(f"Algolia initialized: index={index_name}, filter={self.lang_filter}")
    
    def discover_all(self) -> Generator[str, None, None]:
        """
        Discover all recipe IDs using BFS prefix subdivision.
        
        Yields recipe IDs as they're discovered to enable concurrent downloading.
        """
        if not self.endpoint:
            raise RuntimeError("Algolia client not initialized")
        
        prefix_queue = deque(self.SEARCH_CHARS)
        seen_ids: set[str] = set()
        
        while prefix_queue:
            prefix = prefix_queue.popleft()
            ids, total_hits = self._query_prefix(prefix)
            
            for rid in ids:
                if rid not in seen_ids:
                    seen_ids.add(rid)
                    yield rid
            
            # Subdivide if we hit the limit and there are more results
            if len(ids) >= self.HITS_PER_PAGE and total_hits > self.HITS_PER_PAGE:
                if len(prefix) < self.MAX_DEPTH:
                    for c in self.SEARCH_CHARS:
                        prefix_queue.append(prefix + c)
            
            if len(prefix) == 1:
                log.debug(f"Prefix '{prefix}': found {len(ids)}/{total_hits}, total discovered: {len(seen_ids)}")
    
    def _query_prefix(self, prefix: str) -> tuple[list[str], int]:
        """Query Algolia for recipes matching prefix."""
        payload = {
            "query": prefix,
            "page": 0,
            "hitsPerPage": self.HITS_PER_PAGE,
            "attributesToRetrieve": ["id"],
            "filters": self.lang_filter,
            "restrictSearchableAttributes": ["title"],
        }
        
        req = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Algolia-Application-Id": str(self.app_id),
                "X-Algolia-API-Key": str(self.api_key),
            },
        )
        
        try:
            with urlopen(req, timeout=self.config.request_timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            
            total_hits = data.get("nbHits") or 0
            hits = data.get("hits") or []
            
            ids = []
            for hit in hits:
                if isinstance(hit, dict):
                    rid = hit.get("id") or hit.get("objectID")
                    if isinstance(rid, str) and rid.strip():
                        ids.append(rid.strip())
            
            return ids, total_hits
        
        except Exception as e:
            log.warning(f"Algolia query failed for prefix='{prefix}': {e}")
            return [], 0
