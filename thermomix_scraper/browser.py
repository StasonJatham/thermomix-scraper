"""Browser management using Selenium."""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Generator

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from selenium.webdriver.chrome.webdriver import WebDriver

    from .config import Config

log = logging.getLogger("thermomix.browser")


def create_driver(config: Config) -> WebDriver:
    """Create and configure Chrome WebDriver."""
    options = Options()
    
    if chrome_path := os.getenv("GOOGLE_CHROME_PATH"):
        options.binary_location = chrome_path
    
    if config.headless:
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    
    service = Service(str(config.chromedriver_path))
    return webdriver.Chrome(service=service, options=options)


@contextmanager
def browser_session(config: Config) -> Generator[WebDriver, None, None]:
    """Context manager for browser session with automatic cleanup."""
    driver = create_driver(config)
    try:
        yield driver
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def dismiss_cookie_banner(driver: WebDriver) -> None:
    """Dismiss cookie consent banner if present."""
    try:
        driver.find_element(By.CLASS_NAME, "accept-cookie-container").click()
        time.sleep(0.3)
    except Exception:
        pass


def wait_for_page_load(driver: WebDriver, timeout: float = 10.0) -> None:
    """Wait for page content to load."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, 
                "#ingredients li, .core-ingredient, [class*='ingredient'], script[type='application/ld+json']"
            ))
        )
    except Exception:
        pass


def login(driver: WebDriver, config: Config) -> bool:
    """Attempt login to Cookidoo. Returns True on success."""
    if not config.username or not config.password:
        return False
    
    login_urls = [
        f"{config.base_url}profile/login",
        config.base_url,
    ]
    
    for url in login_urls:
        try:
            driver.get(url)
            time.sleep(config.page_load_timeout)
            dismiss_cookie_banner(driver)
            
            # Check if already logged in
            try:
                driver.find_element(By.TAG_NAME, "core-user-profile")
                log.info("Already logged in")
                return True
            except Exception:
                pass
            
            # Find email input
            email_input = _find_element_by_selectors(driver, [
                'input[type="email"]',
                'input[name="email"]',
                'input[name="username"]',
                'input[id*="email" i]',
                'input[id*="user" i]',
            ])
            
            # Find password input
            pass_input = _find_element_by_selectors(driver, [
                'input[type="password"]',
                'input[name="password"]',
                'input[name*="pass" i]',
                'input[id*="pass" i]',
            ])
            
            if not email_input or not pass_input:
                continue
            
            # Enter credentials
            email_input.clear()
            email_input.send_keys(config.username)
            pass_input.clear()
            pass_input.send_keys(config.password)
            
            # Submit form
            if not _click_submit(driver):
                pass_input.send_keys(Keys.ENTER)
            
            time.sleep(config.page_load_timeout)
            
            # Verify login
            driver.find_element(By.TAG_NAME, "core-user-profile")
            log.info("Login successful")
            return True
            
        except Exception as e:
            log.debug(f"Login attempt failed: {e}")
            continue
    
    return False


def logout(driver: WebDriver, config: Config) -> None:
    """Logout from Cookidoo."""
    try:
        driver.get(f"{config.base_url}profile/logout")
        time.sleep(config.page_load_timeout)
    except Exception:
        pass


def _find_element_by_selectors(driver: WebDriver, selectors: list[str]):
    """Find element using multiple CSS selectors."""
    for selector in selectors:
        try:
            return driver.find_element(By.CSS_SELECTOR, selector)
        except Exception:
            continue
    return None


def _click_submit(driver: WebDriver) -> bool:
    """Click submit button if found."""
    try:
        driver.find_element(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"]').click()
        return True
    except Exception:
        return False
