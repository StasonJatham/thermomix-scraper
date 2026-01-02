"""State management for scraper persistence."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .models import Recipe, ScrapeState

if TYPE_CHECKING:
    from .config import Config

log = logging.getLogger("thermomix.state")


class StateManager:
    """Manages scraper state and recipe storage."""
    
    def __init__(self, config: Config):
        self.config = config
        self.state = ScrapeState()
        self._load_state()
        self._scan_existing_recipes()
    
    def _load_state(self) -> None:
        """Load state from file if exists."""
        if not self.config.state_file or not self.config.state_file.exists():
            return
        
        try:
            with open(self.config.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.state = ScrapeState.from_dict(data)
            log.info(
                f"Loaded state: {len(self.state.pending)} pending, "
                f"{len(self.state.completed)} completed, {len(self.state.failed)} failed"
            )
        except Exception as e:
            log.warning(f"Failed to load state: {e}")
    
    def _scan_existing_recipes(self) -> None:
        """Scan output directory for existing recipe files."""
        if not self.config.output_dir.is_dir():
            return
        
        complete_count = 0
        incomplete_count = 0
        
        for fpath in self.config.output_dir.glob("*.json"):
            if fpath.name.startswith("."):
                continue
            
            recipe_id = fpath.stem
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                recipe = Recipe.from_dict(data)
                self.state.discovered.add(recipe_id)
                
                if recipe.is_complete():
                    self.state.completed.add(recipe_id)
                    self.state.pending.discard(recipe_id)
                    complete_count += 1
                else:
                    self.state.pending.add(recipe_id)
                    incomplete_count += 1
            
            except Exception:
                self.state.discovered.add(recipe_id)
                self.state.completed.add(recipe_id)
                complete_count += 1
        
        if complete_count or incomplete_count:
            log.info(f"Found {complete_count} complete, {incomplete_count} incomplete recipes")
    
    def save_state(self) -> None:
        """Persist current state to file."""
        if not self.config.state_file:
            return
        
        try:
            self.config.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.warning(f"Failed to save state: {e}")
    
    def clear_state(self) -> None:
        """Remove state file on completion."""
        if self.config.state_file and self.config.state_file.exists():
            try:
                self.config.state_file.unlink()
                log.info("State file removed (scan complete)")
            except Exception:
                pass
    
    def recipe_path(self, recipe_id: str) -> Path:
        """Get path for recipe JSON file."""
        return self.config.output_dir / f"{recipe_id}.json"
    
    def recipe_exists(self, recipe_id: str) -> bool:
        """Check if recipe file exists."""
        return self.recipe_path(recipe_id).exists()
    
    def save_recipe(self, recipe: Recipe) -> None:
        """Save recipe to JSON file."""
        path = self.recipe_path(recipe.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(recipe.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load_recipe(self, recipe_id: str) -> Recipe | None:
        """Load recipe from JSON file."""
        path = self.recipe_path(recipe_id)
        if not path.exists():
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                return Recipe.from_dict(json.load(f))
        except Exception:
            return None
    
    def should_download(self, recipe_id: str) -> bool:
        """Determine if recipe should be downloaded based on mode."""
        from .config import RunMode
        
        mode = self.config.mode
        
        if mode == RunMode.REDOWNLOAD_ALL:
            return True
        
        if mode == RunMode.UPDATE:
            return True  # Always download for update
        
        if mode == RunMode.CONTINUE:
            # Download if in pending or failed
            return recipe_id in self.state.pending or recipe_id in self.state.failed
        
        # SKIP_EXISTING (default)
        if recipe_id in self.state.completed:
            return False
        
        return not self.recipe_exists(recipe_id)
    
    def mark_discovered(self, recipe_id: str) -> None:
        """Mark recipe as discovered."""
        self.state.discovered.add(recipe_id)
    
    def mark_pending(self, recipe_id: str) -> None:
        """Mark recipe as pending download."""
        self.state.pending.add(recipe_id)
    
    def mark_completed(self, recipe_id: str) -> None:
        """Mark recipe as successfully downloaded."""
        self.state.completed.add(recipe_id)
        self.state.pending.discard(recipe_id)
        self.state.failed.discard(recipe_id)
    
    def mark_failed(self, recipe_id: str) -> None:
        """Mark recipe as failed."""
        self.state.failed.add(recipe_id)
        self.state.pending.discard(recipe_id)
