"""Recipe parsing from HTML and JSON-LD."""

from __future__ import annotations

import html
import json
import logging
import re
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup

from .models import Recipe

if TYPE_CHECKING:
    from selenium.webdriver.chrome.webdriver import WebDriver

log = logging.getLogger("thermomix.parser")


def parse_recipe(driver: WebDriver, recipe_id: str) -> Recipe:
    """Parse recipe data from page source."""
    page_html = driver.page_source
    soup = BeautifulSoup(page_html, "html.parser")
    
    # Try JSON-LD first (most reliable)
    recipe = _parse_jsonld(soup, recipe_id, driver.current_url)
    if recipe and recipe.is_complete():
        log.debug(f"Parsed {recipe_id} via JSON-LD: {len(recipe.ingredients)} ingredients")
        return recipe
    
    # Fallback to HTML parsing
    recipe = _parse_html(soup, recipe_id, driver.current_url)
    log.debug(f"Parsed {recipe_id} via HTML: {len(recipe.ingredients)} ingredients")
    return recipe


def _parse_jsonld(soup: BeautifulSoup, recipe_id: str, source_url: str | None) -> Recipe | None:
    """Parse recipe from JSON-LD structured data."""
    try:
        for script in soup.select('script[type="application/ld+json"]'):
            if not script.string:
                continue
            
            try:
                data = json.loads(script.string)
            except json.JSONDecodeError:
                continue
            
            for obj in _iter_jsonld_objects(data):
                if not _is_recipe_type(obj):
                    continue
                
                return _extract_recipe_from_jsonld(obj, soup, recipe_id, source_url)
    
    except Exception as e:
        log.debug(f"JSON-LD parsing failed for {recipe_id}: {e}")
    
    return None


def _parse_html(soup: BeautifulSoup, recipe_id: str, source_url: str | None) -> Recipe:
    """Parse recipe from HTML elements (fallback)."""
    rating_score, rating_count = _extract_rating(soup)
    tm_versions = _extract_tm_versions(soup)
    
    ingredients = _extract_by_selectors(soup, [
        "#ingredients li",
        ".core-ingredient",
        "[class*='ingredient-item']",
        ".recipe-ingredients li",
        "[data-ingredient]",
        ".rdp-ingredients li",
    ])
    
    steps = _extract_by_selectors(soup, [
        "#preparation-steps li",
        ".core-step",
        "[class*='step-item']",
        ".recipe-steps li",
        ".rdp-steps li",
        "[data-step]",
    ])
    
    tags = [
        a.text.replace("#", "").replace("\n", "").strip().lower()
        for a in soup.select(".core-tags-wrapper__tags-container a")
        if a.text.strip()
    ]
    
    title = _get_text(soup, ".recipe-card__title") or _get_text(soup, "h1") or _get_text(soup, "title") or ""
    
    html_el = soup.select_one("html")
    language = html_el.get("lang") if html_el else None
    
    return Recipe(
        id=recipe_id,
        source_url=source_url,
        language=language,
        title=html.unescape(title),
        rating_score=rating_score,
        rating_count=rating_count,
        tm_versions=tm_versions,
        ingredients=[html.unescape(i) for i in ingredients],
        steps=[html.unescape(s) for s in steps],
        tags=tags,
    )


def _extract_recipe_from_jsonld(
    obj: dict[str, Any],
    soup: BeautifulSoup,
    recipe_id: str,
    source_url: str | None,
) -> Recipe:
    """Extract recipe data from JSON-LD object."""
    rating_score, rating_count = _extract_rating(soup)
    tm_versions = _extract_tm_versions(soup)
    
    # Decode HTML entities in ingredients
    raw_ingredients = obj.get("recipeIngredient") or []
    ingredients = [html.unescape(str(i)) for i in raw_ingredients]
    
    # Extract steps with HTML entity decoding
    raw_steps = _flatten_steps(obj.get("recipeInstructions"))
    steps = [html.unescape(s) for s in raw_steps]
    
    # Extract nutrition
    nutritions = {}
    nutrition_data = obj.get("nutrition")
    if isinstance(nutrition_data, dict):
        for k, v in nutrition_data.items():
            if not k.startswith("@"):
                nutritions[str(k).lower()] = str(v) if v is not None else None
    
    # Extract tags from keywords and categories
    tags = _extract_tags(obj)
    
    # Use aggregateRating as fallback
    if rating_score is None:
        ar = obj.get("aggregateRating")
        if isinstance(ar, dict):
            rating_score = ar.get("ratingValue")
            rating_count = ar.get("ratingCount")
    
    html_el = soup.select_one("html")
    language = obj.get("inLanguage") or (html_el.get("lang") if html_el else None)
    
    return Recipe(
        id=recipe_id,
        source_url=source_url,
        language=language,
        title=html.unescape(obj.get("name") or ""),
        rating_score=rating_score,
        rating_count=rating_count,
        tm_versions=tm_versions,
        ingredients=ingredients,
        steps=steps,
        tags=tags,
        nutritions=nutritions,
    )


def _iter_jsonld_objects(node: Any):
    """Iterate through JSON-LD objects, handling nesting patterns."""
    if node is None:
        return
    
    if isinstance(node, dict):
        yield node
        for key in ("@graph", "mainEntity", "mainEntityOfPage", "itemListElement", "hasPart"):
            if key in node:
                yield from _iter_jsonld_objects(node[key])
    
    elif isinstance(node, list):
        for item in node:
            yield from _iter_jsonld_objects(item)


def _is_recipe_type(obj: dict[str, Any]) -> bool:
    """Check if JSON-LD object is a Recipe type."""
    obj_type = obj.get("@type")
    if isinstance(obj_type, list):
        return any(t.lower() == "recipe" for t in obj_type if isinstance(t, str))
    return isinstance(obj_type, str) and obj_type.lower() == "recipe"


def _flatten_steps(node: Any) -> list[str]:
    """Extract step texts from recipeInstructions (supports nesting)."""
    steps = []
    
    if node is None:
        return steps
    
    if isinstance(node, str):
        txt = node.strip()
        return [txt] if txt else []
    
    if isinstance(node, dict):
        txt = node.get("text")
        if isinstance(txt, str) and txt.strip():
            steps.append(txt.strip())
        
        for key in ("itemListElement", "steps", "step", "elements"):
            if key in node:
                for child in _ensure_list(node.get(key)):
                    steps.extend(_flatten_steps(child))
        return steps
    
    if isinstance(node, list):
        for item in node:
            steps.extend(_flatten_steps(item))
    
    return steps


def _extract_tags(obj: dict[str, Any]) -> list[str]:
    """Extract and normalize tags from JSON-LD."""
    tags = []
    
    # Keywords
    keywords = obj.get("keywords")
    if isinstance(keywords, str):
        tags.extend(t.strip() for t in keywords.split(",") if t.strip())
    elif isinstance(keywords, list):
        tags.extend(str(t).strip() for t in keywords if str(t).strip())
    
    # Categories and cuisine
    for key in ("recipeCategory", "recipeCuisine"):
        for t in _ensure_list(obj.get(key)):
            if isinstance(t, str) and t.strip():
                tags.extend(p.strip() for p in t.split(",") if p.strip())
    
    # Normalize and dedupe
    seen = set()
    normalized = []
    for t in tags:
        lower = t.lower()
        if lower and lower not in seen:
            seen.add(lower)
            normalized.append(lower)
    
    return normalized


def _extract_rating(soup: BeautifulSoup) -> tuple[float | None, int | None]:
    """Extract rating score and count from HTML."""
    score = None
    count = None
    
    rating_container = soup.select_one("core-rating")
    if rating_container:
        counter = rating_container.select_one(".core-rating__counter")
        if counter:
            try:
                score = float(counter.text.strip())
            except (ValueError, TypeError):
                pass
        
        label = rating_container.select_one(".core-rating__label")
        if label:
            txt = label.text.strip()
            m = re.search(r"\d+", txt.replace(".", "").replace(",", ""))
            if m:
                try:
                    count = int(m.group())
                except (ValueError, TypeError):
                    pass
    
    return score, count


def _extract_tm_versions(soup: BeautifulSoup) -> list[str]:
    """Extract TM versions (TM5, TM6, TM7) from page."""
    versions = []
    
    for el in soup.select(".rdp-tm-versions__name, [class*='tm-version']"):
        txt = el.text.strip()
        for tm in ("TM5", "TM6", "TM7"):
            if tm in txt and tm not in versions:
                versions.append(tm)
    
    if not versions:
        header = soup.select_one(".recipe-card__header, .rdp-header")
        if header:
            txt = header.text
            for tm in ("TM5", "TM6", "TM7"):
                if tm in txt and tm not in versions:
                    versions.append(tm)
    
    return sorted(versions)


def _extract_by_selectors(soup: BeautifulSoup, selectors: list[str]) -> list[str]:
    """Extract text from first matching selector."""
    for selector in selectors:
        items = soup.select(selector)
        if items:
            result = [re.sub(r" +", " ", li.text).replace("\n", " ").strip() for li in items]
            result = [i for i in result if i]
            if result:
                return result
    return []


def _get_text(soup: BeautifulSoup, selector: str) -> str | None:
    """Get text from selector or None."""
    el = soup.select_one(selector)
    return el.text.strip() if el else None


def _ensure_list(value: Any) -> list:
    """Ensure value is a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
