"""JSON-based persistent cache for the keyword registry."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

from ai_rpa.registry.library_scanner import LibraryInfo

logger = logging.getLogger(__name__)

CACHE_VERSION = 1
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours


def _cache_path(config) -> Path:
    """Get the cache file path from config."""
    path = config.registry_cache_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_cache(config) -> Optional[list[LibraryInfo]]:
    """Load cached library info from disk. Returns None if cache is invalid."""
    path = _cache_path(config)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read cache: %s", e)
        return None

    # Version check
    if data.get("version") != CACHE_VERSION:
        logger.info("Cache version mismatch, rebuilding")
        return None

    # TTL check
    cached_at = data.get("cached_at", 0)
    if time.time() - cached_at > CACHE_TTL_SECONDS:
        logger.info("Cache expired, rebuilding")
        return None

    # Check if extra_libraries match
    cached_libs = set(data.get("extra_libraries", []))
    requested_libs = set(config.extra_libraries)
    if cached_libs != requested_libs:
        logger.info("Extra libraries changed, rebuilding cache")
        return None

    # Reconstruct
    try:
        libraries = [LibraryInfo.from_dict(lib) for lib in data.get("libraries", [])]
        logger.info("Loaded %d libraries from cache", len(libraries))
        return libraries
    except Exception as e:
        logger.warning("Failed to parse cache: %s", e)
        return None


def save_cache(config, libraries: list[LibraryInfo]) -> None:
    """Save library info to disk cache."""
    path = _cache_path(config)
    data = {
        "version": CACHE_VERSION,
        "cached_at": time.time(),
        "extra_libraries": config.extra_libraries,
        "libraries": [lib.to_dict() for lib in libraries],
    }
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Saved cache with %d libraries to %s", len(libraries), path)
    except OSError as e:
        logger.warning("Failed to write cache: %s", e)
