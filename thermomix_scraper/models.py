"""Data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Recipe:
    """Recipe data model."""
    
    id: str
    title: str = ""
    source_url: str | None = None
    language: str | None = None
    rating_score: float | None = None
    rating_count: int | None = None
    tm_versions: list[str] = field(default_factory=list)
    ingredients: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    nutritions: dict[str, str | None] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "source_url": self.source_url,
            "language": self.language,
            "title": self.title,
            "rating_count": self.rating_count,
            "rating_score": self.rating_score,
            "tm_versions": self.tm_versions,
            "ingredients": self.ingredients,
            "nutritions": self.nutritions,
            "steps": self.steps,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Recipe:
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            source_url=data.get("source_url"),
            language=data.get("language"),
            rating_score=data.get("rating_score"),
            rating_count=data.get("rating_count"),
            tm_versions=data.get("tm_versions") or data.get("tm-versions") or [],
            ingredients=data.get("ingredients") or [],
            steps=data.get("steps") or [],
            tags=data.get("tags") or [],
            nutritions=data.get("nutritions") or {},
        )
    
    def is_complete(self) -> bool:
        """Check if recipe has meaningful content."""
        return bool(self.ingredients or self.steps)


@dataclass
class ScrapeState:
    """Scraper state for resume capability."""
    
    discovered: set[str] = field(default_factory=set)
    pending: set[str] = field(default_factory=set)
    completed: set[str] = field(default_factory=set)
    failed: set[str] = field(default_factory=set)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "discovered": sorted(self.discovered),
            "pending": sorted(self.pending),
            "completed": sorted(self.completed),
            "failed": sorted(self.failed),
            "last_updated": self.last_updated.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScrapeState:
        """Create from dictionary."""
        last_updated = data.get("last_updated")
        if isinstance(last_updated, str):
            try:
                last_updated = datetime.fromisoformat(last_updated)
            except ValueError:
                last_updated = datetime.now()
        elif last_updated is None:
            last_updated = datetime.now()
        
        return cls(
            discovered=set(data.get("discovered") or []),
            pending=set(data.get("pending") or []),
            completed=set(data.get("completed") or []),
            failed=set(data.get("failed") or []),
            last_updated=last_updated,
        )


@dataclass
class ScrapeStats:
    """Scraping statistics."""
    
    discovered: int = 0
    downloaded: int = 0
    skipped: int = 0
    updated: int = 0
    failures: int = 0
    prefixes_queried: int = 0
    
    def __str__(self) -> str:
        parts = [f"discovered={self.discovered}"]
        if self.downloaded:
            parts.append(f"downloaded={self.downloaded}")
        if self.updated:
            parts.append(f"updated={self.updated}")
        if self.skipped:
            parts.append(f"skipped={self.skipped}")
        if self.failures:
            parts.append(f"failures={self.failures}")
        return ", ".join(parts)
