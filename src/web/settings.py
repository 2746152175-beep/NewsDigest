"""Read/write web settings: model/base_url in config.yaml, api key in .env."""

import json
import re
from pathlib import Path

from src.config_loader import PROJECT_ROOT, load_config, load_taxonomy

CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
ENV_PATH = PROJECT_ROOT / ".env"
API_KEY_ENV = "LLM_API_KEY"

_ENV_KEY_RE = re.compile(r"^LLM_API_KEY\s*=")


def _read_api_key() -> str:
    if not ENV_PATH.exists():
        return ""
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if _ENV_KEY_RE.match(line.strip()):
            _, _, value = line.partition("=")
            return value.strip().strip('"').strip("'")
    return ""


def read_settings() -> dict:
    config = load_config()
    taxonomy = load_taxonomy()
    llm = config.get("llm") or {}
    fetch_cfg = config.get("fetch") or {}
    filter_cfg = config.get("filter") or {}
    return {
        "model": llm.get("model", ""),
        "base_url": llm.get("base_url", ""),
        "api_key": _read_api_key(),
        "max_items": int(fetch_cfg.get("max_items", 60) or 60),
        "importance_min": int(filter_cfg.get("importance_min", 0) or 0),
        "segments": list(filter_cfg.get("segments") or []),
        "all_segments": list(taxonomy.get("segments") or []),
        "groups": dict(taxonomy.get("groups") or {}),
    }


def _yaml_value(value) -> str:
    """Render a Python value as a single-line YAML scalar/list for in-place writes."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(str(value), ensure_ascii=False)


def _replace_yaml_key(lines: list[str], key: str, value_yaml: str) -> list[str]:
    pattern = re.compile(rf"^(?P<indent>\s*){re.escape(key)}:(?P<rest>.*)$")
    out: list[str] = []
    for line in lines:
        content = line.rstrip("\r\n")
        terminator = line[len(content) :]
        match = pattern.match(content)
        if match:
            rest = match.group("rest")
            comment = ""
            if "#" in rest:
                comment = " " + rest[rest.index("#") :]
            out.append(f'{match.group("indent")}{key}: {value_yaml}{comment}{terminator}')
        else:
            out.append(line)
    return out


def _write_config(
    model: str,
    base_url: str,
    max_items: int | None = None,
    importance_min: int | None = None,
    segments: list[str] | None = None,
) -> None:
    lines = CONFIG_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
    lines = _replace_yaml_key(lines, "model", _yaml_value(model))
    lines = _replace_yaml_key(lines, "base_url", _yaml_value(base_url))
    if max_items is not None:
        lines = _replace_yaml_key(lines, "max_items", _yaml_value(max_items))
    if importance_min is not None:
        lines = _replace_yaml_key(lines, "importance_min", _yaml_value(importance_min))
    if segments is not None:
        lines = _replace_yaml_key(lines, "segments", _yaml_value(segments))
    CONFIG_PATH.write_text("".join(lines), encoding="utf-8")


def _write_env(api_key: str) -> None:
    text = ENV_PATH.read_text(encoding="utf-8") if ENV_PATH.exists() else ""
    lines = text.splitlines(keepends=True)
    found = False
    for index, line in enumerate(lines):
        if _ENV_KEY_RE.match(line.strip()):
            lines[index] = f"{API_KEY_ENV}={api_key}\n"
            found = True
    if not found:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(f"{API_KEY_ENV}={api_key}\n")
    ENV_PATH.write_text("".join(lines), encoding="utf-8")


def write_settings(
    model: str,
    base_url: str,
    api_key: str,
    max_items: int | None = None,
    importance_min: int | None = None,
    segments: list[str] | None = None,
) -> None:
    _write_config(model, base_url, max_items, importance_min, segments)
    _write_env(api_key)
