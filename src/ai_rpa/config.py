"""Configuration management for AI-RPA."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


def _find_config_file() -> Optional[Path]:
    """Search for .airpa.toml in current dir and home dir."""
    for directory in [Path.cwd(), Path.home()]:
        config = directory / ".airpa.toml"
        if config.exists():
            return config
    return None


def _load_toml_config(path: Path) -> dict:
    """Load a simple TOML config (minimal parser, no dependency)."""
    config = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("["):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            config[key] = value
    return config


@dataclass
class AirPaConfig:
    """AI-RPA configuration."""

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_base_url: Optional[str] = None
    max_retries: int = 3
    registry_cache_path: Path = field(
        default_factory=lambda: Path.home() / ".airpa" / "registry_cache.json"
    )
    extra_libraries: list[str] = field(default_factory=list)
    language: str = "zh"
    verbose: bool = False
    dry_run: bool = False

    @classmethod
    def load(cls, **overrides) -> "AirPaConfig":
        """Load config from: env vars → .airpa.toml → defaults → overrides."""
        cfg = {}

        # Load from .airpa.toml
        config_file = _find_config_file()
        if config_file:
            cfg.update(_load_toml_config(config_file))

        # Environment variables take precedence
        env_map = {
            "openai_api_key": "AIRPA_OPENAI_API_KEY",
            "openai_model": "AIRPA_OPENAI_MODEL",
            "openai_base_url": "AIRPA_OPENAI_BASE_URL",
            "language": "AIRPA_LANGUAGE",
        }
        for field_name, env_var in env_map.items():
            value = os.environ.get(env_var)
            if value:
                cfg[field_name] = value

        # CLI overrides take highest priority
        cfg.update({k: v for k, v in overrides.items() if v is not None})

        # Type conversions
        if "max_retries" in cfg:
            cfg["max_retries"] = int(cfg["max_retries"])
        if "verbose" in cfg:
            cfg["verbose"] = str(cfg["verbose"]).lower() in ("true", "1", "yes")
        if "dry_run" in cfg:
            cfg["dry_run"] = str(cfg["dry_run"]).lower() in ("true", "1", "yes")

        # Filter to only valid fields
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in cfg.items() if k in valid_fields}

        return cls(**filtered)
