"""Main scraper logic."""

from __future__ import annotations

import logging
import threading
import time
from queue import Empty, Queue
from typing import TYPE_CHECKING

from selenium.webdriver.common.by import By

from .algolia import AlgoliaClient
from .browser import browser_session, dismiss_cookie_banner, login, logout, wait_for_page_load
from .config import RunMode
from .models import ScrapeStats
from .parser import parse_recipe
from .state import StateManager

if TYPE_CHECKING:
    from selenium.webdriver.chrome.webdriver import WebDriver

    from .config import Config

log = logging.getLogger("thermomix.scraper")


class RecipeScraper:
    """Thermomix recipe scraper."""
    
    def __init__(self, config: Config):
        self.config = config
        self.state = StateManager(config)
        self.algolia = AlgoliaClient(config)
        self.stats = ScrapeStats()
        
        self._download_queue: Queue[str] = Queue()
        self._discovery_done = threading.Event()
        self._lock = threading.Lock()
    
    def run(self) -> ScrapeStats:
        """Execute the scrape operation."""
        log.info("Starting Thermomix scraper")
        log.info(f"Mode: {self.config.mode.value}, Output: {self.config.output_dir}")
        
        with browser_session(self.config) as driver:
            self._run_with_driver(driver)
        
        return self.stats
    
    def _run_with_driver(self, driver: WebDriver) -> None:
        """Run scraping with browser driver."""
        # Login
        if not login(driver, self.config):
            raise RuntimeError("Login failed - check credentials")
        
        # Handle specific recipe IDs
        if self.config.recipe_ids:
            self._scrape_specific_recipes(driver)
            logout(driver, self.config)
            return
        
        # Full discovery mode
        self._run_discovery_and_download(driver)
        logout(driver, self.config)
    
    def _scrape_specific_recipes(self, driver: WebDriver) -> None:
        """Scrape specific recipe IDs."""
        recipe_ids = [self._normalize_id(rid) for rid in self.config.recipe_ids]
        recipe_ids = [rid for rid in recipe_ids if rid]
        
        log.info(f"Scraping {len(recipe_ids)} specific recipes")
        
        for recipe_id in recipe_ids:
            if not self.state.should_download(recipe_id):
                log.debug(f"Skipping {recipe_id} (already exists)")
                self.stats.skipped += 1
                continue
            
            success = self._download_recipe(driver, recipe_id)
            if success:
                self.stats.downloaded += 1
            else:
                self.stats.failures += 1
        
        log.info(f"Complete: {self.stats}")
    
    def _run_discovery_and_download(self, driver: WebDriver) -> None:
        """Run concurrent discovery and download."""
        # Initialize Algolia
        self.algolia.initialize(driver)
        
        # Check if resuming from state
        if self.config.mode == RunMode.CONTINUE and self.state.state.pending:
            log.info(f"Resuming: {len(self.state.state.pending)} pending recipes")
            for rid in self.state.state.pending:
                self._download_queue.put(rid)
            self._discovery_done.set()
        else:
            # Start discovery thread
            discovery_thread = threading.Thread(target=self._discovery_worker, daemon=True)
            discovery_thread.start()
        
        # Download in main thread (Selenium isn't thread-safe)
        self._download_worker(driver)
        
        # Final state save
        self.state.save_state()
        
        # Clean up state if complete
        if not self.state.state.pending and self.stats.failures == 0:
            self.state.clear_state()
        
        log.info(f"Complete: {self.stats}")
    
    def _discovery_worker(self) -> None:
        """Discover recipe IDs via Algolia."""
        try:
            for recipe_id in self.algolia.discover_all():
                self.state.mark_discovered(recipe_id)
                
                with self._lock:
                    self.stats.discovered = len(self.state.state.discovered)
                
                if not self.state.should_download(recipe_id):
                    with self._lock:
                        self.stats.skipped += 1
                    continue
                
                self.state.mark_pending(recipe_id)
                self._download_queue.put(recipe_id)
                
                # Progress logging
                if self.stats.discovered % 100 == 0:
                    log.info(f"Discovery progress: {self.stats.discovered} found, {self._download_queue.qsize()} queued")
                
                time.sleep(self.config.algolia_delay)
        
        except Exception as e:
            log.error(f"Discovery failed: {e}")
        
        finally:
            self._discovery_done.set()
            log.info(f"Discovery complete: {len(self.state.state.discovered)} recipes")
    
    def _download_worker(self, driver: WebDriver) -> None:
        """Process download queue."""
        downloads_since_save = 0
        
        while True:
            try:
                recipe_id = self._download_queue.get(timeout=2.0)
            except Empty:
                if self._discovery_done.is_set() and self._download_queue.empty():
                    break
                continue
            
            success = self._download_recipe(driver, recipe_id)
            
            with self._lock:
                if success:
                    self.stats.downloaded += 1
                    self.state.mark_completed(recipe_id)
                else:
                    self.stats.failures += 1
                    self.state.mark_failed(recipe_id)
            
            downloads_since_save += 1
            
            # Periodic state save and logging
            if downloads_since_save >= self.config.save_interval:
                self.state.save_state()
                log.info(f"Progress: {self.stats}")
                downloads_since_save = 0
            
            self._download_queue.task_done()
    
    def _download_recipe(self, driver: WebDriver, recipe_id: str) -> bool:
        """Download and save a single recipe."""
        url = f"{self.config.base_url}recipes/recipe/{self.config.url_locale}/{recipe_id}"
        
        for attempt in range(self.config.max_retries + 1):
            try:
                driver.get(url)
                time.sleep(self.config.page_load_timeout)
                wait_for_page_load(driver)
                time.sleep(1.0)  # Extra JS load time
                
                dismiss_cookie_banner(driver)
                self._remove_base_tag(driver)
                
                recipe = parse_recipe(driver, recipe_id)
                
                # Validate content
                if not recipe.is_complete():
                    if attempt < self.config.max_retries:
                        log.debug(f"Empty content for {recipe_id}, retry {attempt + 1}")
                        time.sleep(self.config.retry_delay)
                        continue
                    log.warning(f"Empty content for {recipe_id}")
                
                self.state.save_recipe(recipe)
                time.sleep(self.config.download_delay)
                return True
            
            except Exception as e:
                if attempt < self.config.max_retries:
                    time.sleep(self.config.retry_delay)
                    continue
                log.error(f"Failed {recipe_id}: {e}")
                return False
        
        return False
    
    def _remove_base_tag(self, driver: WebDriver) -> None:
        """Remove base tag that interferes with parsing."""
        try:
            driver.execute_script(
                "var el = arguments[0]; el.parentNode.removeChild(el);",
                driver.find_element(By.TAG_NAME, "base"),
            )
        except Exception:
            pass
    
    @staticmethod
    def _normalize_id(recipe_id: str) -> str | None:
        """Normalize recipe ID format."""
        rid = str(recipe_id).strip()
        if not rid:
            return None
        if rid[0].isdigit():
            rid = "r" + rid
        if not rid.startswith("r"):
            rid = "r" + rid.lstrip("r")
        return rid


def scrape(config: Config) -> ScrapeStats:
    """Main entry point for scraping."""
    scraper = RecipeScraper(config)
    return scraper.run()
