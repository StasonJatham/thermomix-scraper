#!/usr/bin/env python3
"""Thermomix recipe scraper - main entry point."""

from __future__ import annotations

import argparse
import sys

from .config import Config, RunMode, setup_logging
from .scraper import scrape


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Thermomix recipe scraper for Cookidoo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Run modes:
  skip        Skip already downloaded recipes (default)
  update      Re-download and update all recipes
  redownload  Force re-download everything from scratch
  continue    Continue from last saved state

Environment variables (override with CLI args):
  THERMOMIX_LOCALE      Cookidoo locale (e.g., "de", "en-GB")
  THERMOMIX_USERNAME    Account email/username
  THERMOMIX_PASSWORD    Account password
  THERMOMIX_OUTPUT      Output directory (default: /data)
  THERMOMIX_MODE        Run mode (skip/update/redownload/continue)
  THERMOMIX_RECIPE_IDS  Comma-separated recipe IDs
  THERMOMIX_DEBUG       Enable debug logging (1/true)
""",
    )
    
    parser.add_argument(
        "--mode", "-m",
        type=str,
        choices=["skip", "update", "redownload", "continue"],
        help="Run mode (default: skip existing)",
    )
    parser.add_argument(
        "--locale", "-l",
        type=str,
        help="Cookidoo locale (e.g., 'de', 'en-GB')",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output directory for recipes",
    )
    parser.add_argument(
        "--username", "-u",
        type=str,
        help="Cookidoo account email",
    )
    parser.add_argument(
        "--password", "-p",
        type=str,
        help="Cookidoo account password",
    )
    parser.add_argument(
        "--recipe-id", "-r",
        action="append",
        dest="recipe_ids",
        help="Specific recipe ID(s) to download (can repeat)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=None,
        help="Run browser headless",
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug logging",
    )
    
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    # Load config from environment first
    config = Config.from_env()
    
    # Override with CLI arguments
    if args.mode:
        config.mode = RunMode(args.mode)
    if args.locale:
        config.locale = args.locale
    if args.output:
        config.output_dir = args.output
    if args.username:
        config.username = args.username
    if args.password:
        config.password = args.password
    if args.recipe_ids:
        config.recipe_ids = args.recipe_ids
    if args.headless is not None:
        config.headless = args.headless
    if args.debug:
        config.debug = True
    
    # Re-initialize paths
    config.__post_init__()
    
    # Setup logging
    log = setup_logging(config)
    
    # Validate required config
    if not config.locale:
        log.error("Locale required (THERMOMIX_LOCALE or --locale)")
        return 1
    
    if not config.username or not config.password:
        log.error("Credentials required (THERMOMIX_USERNAME/PASSWORD or --username/--password)")
        return 1
    
    try:
        stats = scrape(config)
        
        if stats.failures > 0:
            log.warning(f"Completed with {stats.failures} failures")
            return 1
        
        return 0
    
    except KeyboardInterrupt:
        log.info("Interrupted by user")
        return 130
    
    except Exception as e:
        log.exception(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
