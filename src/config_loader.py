"""Unified loader for config/*.yaml files."""

import os
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a YAML file with yaml.safe_load and return a dict."""
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


_ENV_PATH = PROJECT_ROOT / ".env"


def load_env(path: Path = _ENV_PATH) -> None:
    """Load KEY=VALUE lines from .env into os.environ (existing env wins)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_config() -> dict[str, Any]:
    """Load config/config.yaml, loading .env first so keys are available."""
    load_env()
    return load_yaml_file(PROJECT_ROOT / "config" / "config.yaml")


def load_sources() -> dict[str, Any]:
    """Load config/sources.yaml."""
    return load_yaml_file(PROJECT_ROOT / "config" / "sources.yaml")


def load_watchlist() -> dict[str, Any]:
    """Load config/watchlist.yaml."""
    return load_yaml_file(PROJECT_ROOT / "config" / "watchlist.yaml")


def load_taxonomy() -> dict[str, Any]:
    """Load config/taxonomy.yaml."""
    return load_yaml_file(PROJECT_ROOT / "config" / "taxonomy.yaml")


def resolve_path(value: str) -> Path:
    """Resolve a config path relative to the project root when relative."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path
