"""Pattern store: accumulate and reuse successful automation patterns."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """A proven, reusable automation pattern."""

    id: str
    task_description: str        # Original natural language task
    categories: list[str]        # e.g. ["file", "browser"]
    robot_text: str              # The working .robot script
    libraries_needed: list[str]  # Required libraries
    explanation: str             # What the script does
    keywords_used: list[str]     # Keywords used in the script
    success_count: int = 0       # How many times it ran successfully
    fail_count: int = 0          # How many times it failed after being saved
    created_at: float = 0.0
    last_used_at: float = 0.0
    tags: list[str] = field(default_factory=list)  # User tags

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_description": self.task_description,
            "categories": self.categories,
            "robot_text": self.robot_text,
            "libraries_needed": self.libraries_needed,
            "explanation": self.explanation,
            "keywords_used": self.keywords_used,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Pattern":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def reliability(self) -> float:
        """Reliability score 0-1 based on success/fail ratio."""
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.5
        return self.success_count / total

    @property
    def recency_score(self) -> float:
        """Score 0-1 based on how recently it was used (1 = just now)."""
        if self.last_used_at == 0:
            return 0.0
        age_hours = (time.time() - self.last_used_at) / 3600
        return max(0, 1 - age_hours / 720)  # Decay over 30 days


def _similarity(text_a: str, text_b: str) -> float:
    """Calculate text similarity between two strings (0-1)."""
    return SequenceMatcher(None, text_a.lower(), text_b.lower()).ratio()


def _extract_keywords(robot_text: str) -> list[str]:
    """Extract keyword names from a .robot script."""
    keywords = []
    in_keywords_section = False
    for line in robot_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("*** Test Cases ***"):
            in_keywords_section = True
            continue
        if stripped.startswith("***"):
            in_keywords_section = False
            continue
        if in_keywords_section and stripped and not stripped.endswith("***") and len(stripped.split()) >= 1:
            # Lines indented with keywords (start with spaces)
            if line.startswith("    ") or line.startswith("\t"):
                first_word = stripped.split()[0]
                # Skip variable assignments and control flow
                if not first_word.startswith("${") and first_word not in (
                    "FOR", "END", "IF", "ELSE", "WHILE", "TRY", "EXCEPT",
                    "RETURN", "BREAK", "CONTINUE",
                ):
                    keywords.append(first_word)
    return keywords


class PatternStore:
    """Persistent store of proven automation patterns.

    Enables the "越用越好用" (gets better with use) experience:
    - New tasks are matched against historical patterns first (free, instant)
    - Only unmatched tasks go to AI generation (costs money, slower)
    - Successful executions are saved for future reuse
    """

    def __init__(self, store_path: Optional[Path] = None):
        if store_path is None:
            store_path = Path.home() / ".airpa" / "patterns.json"
        self._path = store_path
        self._patterns: dict[str, Pattern] = {}
        self._load()

    def _load(self):
        """Load patterns from disk."""
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for p in data.get("patterns", []):
                pattern = Pattern.from_dict(p)
                self._patterns[pattern.id] = pattern
            logger.info("Loaded %d patterns from %s", len(self._patterns), self._path)
        except Exception as e:
            logger.warning("Failed to load patterns: %s", e)

    def _save(self):
        """Save patterns to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "patterns": [p.to_dict() for p in self._patterns.values()],
        }
        try:
            self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as e:
            logger.warning("Failed to save patterns: %s", e)

    def add(self, task: str, categories: list[str], robot_text: str,
            libraries_needed: list[str], explanation: str) -> Pattern:
        """Save a new successful pattern."""
        import hashlib
        # Generate ID from content hash
        content = f"{task}:{robot_text}"
        pattern_id = hashlib.md5(content.encode()).hexdigest()[:12]

        keywords_used = _extract_keywords(robot_text)
        now = time.time()

        # Check if same pattern already exists (update it)
        if pattern_id in self._patterns:
            existing = self._patterns[pattern_id]
            existing.success_count += 1
            existing.last_used_at = now
            self._save()
            return existing

        pattern = Pattern(
            id=pattern_id,
            task_description=task,
            categories=categories,
            robot_text=robot_text,
            libraries_needed=libraries_needed,
            explanation=explanation,
            keywords_used=keywords_used,
            success_count=1,
            fail_count=0,
            created_at=now,
            last_used_at=now,
        )
        self._patterns[pattern_id] = pattern
        self._save()
        logger.info("Saved new pattern '%s' (id=%s)", task[:50], pattern_id)
        return pattern

    def search(self, task: str, categories: Optional[list[str]] = None,
               min_similarity: float = 0.5, top_k: int = 3) -> list[tuple[Pattern, float]]:
        """Search for similar patterns. Returns list of (pattern, similarity_score).

        Args:
            task: Natural language task description.
            categories: Optional category filter.
            min_similarity: Minimum similarity threshold (0-1).
            top_k: Maximum number of results.
        """
        results = []
        for pattern in self._patterns.values():
            # Category filter
            if categories and not any(c in pattern.categories for c in categories):
                continue

            # Skip unreliable patterns
            if pattern.reliability < 0.3:
                continue

            # Text similarity
            sim = _similarity(task, pattern.task_description)

            # Boost by reliability and recency
            score = sim * 0.6 + pattern.reliability * 0.25 + pattern.recency_score * 0.15

            if score >= min_similarity:
                results.append((pattern, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def record_success(self, pattern_id: str):
        """Record a successful execution of a pattern."""
        if pattern_id in self._patterns:
            self._patterns[pattern_id].success_count += 1
            self._patterns[pattern_id].last_used_at = time.time()
            self._save()

    def record_failure(self, pattern_id: str):
        """Record a failed execution of a pattern."""
        if pattern_id in self._patterns:
            self._patterns[pattern_id].fail_count += 1
            self._save()

    def get_by_id(self, pattern_id: str) -> Optional[Pattern]:
        """Get a pattern by its ID."""
        return self._patterns.get(pattern_id)

    def list_all(self) -> list[Pattern]:
        """List all stored patterns, sorted by success count."""
        return sorted(self._patterns.values(), key=lambda p: p.success_count, reverse=True)

    def count(self) -> int:
        """Total number of stored patterns."""
        return len(self._patterns)

    def delete(self, pattern_id: str) -> bool:
        """Delete a pattern by ID."""
        if pattern_id in self._patterns:
            del self._patterns[pattern_id]
            self._save()
            return True
        return False

    def search_by_tags(self, tags: list[str]) -> list[Pattern]:
        """Search patterns by tags."""
        results = []
        for pattern in self._patterns.values():
            if any(t in pattern.tags for t in tags):
                results.append(pattern)
        return sorted(results, key=lambda p: p.success_count, reverse=True)
