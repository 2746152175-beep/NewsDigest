"""R5-a FastAPI backend for the news agent."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.config_loader import load_config, resolve_path
from src.web import settings as web_settings
from src.web.runner import runner
from src.write.favorites import build_favorite_index, find_note_by_id, load_favorites, set_favorite, set_note_starred
from src.write.obsidian import list_note_dates, load_notes_by_date

INDEX_PATH = Path(__file__).resolve().parent.parent.parent / "static" / "index.html"

app = FastAPI(title="News Agent", version="R5-b")


class SettingsBody(BaseModel):
    model: str
    base_url: str
    api_key: str
    max_items: int | None = None
    importance_min: int | None = None
    segments: list[str] | None = None
    vault_news_dir: str | None = None


class FavoriteBody(BaseModel):
    id: str
    starred: bool


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    if not INDEX_PATH.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return HTMLResponse(INDEX_PATH.read_text(encoding="utf-8"))


@app.post("/api/refresh")
def refresh(date: str | None = None) -> dict:
    if date is not None:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD") from exc
    task_id = runner.start(date)
    if task_id is None:
        raise HTTPException(status_code=409, detail="pipeline already running")
    return {"task_id": task_id, "status": "running"}


@app.get("/api/status")
def status() -> dict:
    return runner.status()


@app.get("/api/news")
def news(date: str) -> list:
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD") from exc

    config = load_config()
    summarized_dir = resolve_path(
        (config.get("data") or {}).get("summarized_dir") or "data/summarized"
    )
    path = summarized_dir / f"{date}.json"
    payload: list = []
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = []
        if isinstance(data, list):
            payload = data
    if not payload:
        payload = load_notes_by_date(config, date)
    favorites = load_favorites(config)
    for it in payload:
        if isinstance(it, dict):
            it["starred"] = str(it.get("id") or "") in favorites
    return payload


@app.get("/api/dates")
def dates() -> list[str]:
    config = load_config()
    tz = ZoneInfo((config.get("project") or {}).get("timezone") or "Asia/Shanghai")
    today = datetime.now(tz).date()
    earliest = today - timedelta(days=1)  # 默认最早到昨天
    summarized_dir = resolve_path(
        (config.get("data") or {}).get("summarized_dir") or "data/summarized"
    )
    if summarized_dir.exists():
        for path in summarized_dir.glob("*.json"):
            try:
                d = datetime.strptime(path.stem, "%Y-%m-%d").date()
            except ValueError:
                continue
            if d < earliest:
                earliest = d
    for d_str in list_note_dates(config):
        try:
            d = datetime.strptime(d_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if d < earliest:
            earliest = d
    return [(today - timedelta(days=i)).isoformat() for i in range((today - earliest).days + 1)]


@app.post("/api/favorite")
def favorite(body: FavoriteBody) -> dict:
    config = load_config()
    set_favorite(config, body.id, body.starred)
    vault = config.get("vault") or {}
    news_dir = Path(str(vault.get("news_dir") or ""))
    if news_dir.is_absolute():
        company_dir = news_dir / (str(vault.get("company_dir") or "01-公司"))
        note_path = find_note_by_id(company_dir, body.id)
        if note_path is not None:
            set_note_starred(note_path, body.starred)
            index_dir = news_dir / (str(vault.get("index_dir") or "00-索引"))
            index_dir.mkdir(parents=True, exist_ok=True)
            (index_dir / "收藏.md").write_text(build_favorite_index(company_dir), encoding="utf-8")
    return {"id": body.id, "starred": body.starred}


@app.get("/api/settings")
def get_settings() -> dict:
    return web_settings.read_settings()


@app.post("/api/settings")
def post_settings(body: SettingsBody) -> dict:
    web_settings.write_settings(
        body.model,
        body.base_url,
        body.api_key,
        max_items=body.max_items,
        importance_min=body.importance_min,
        segments=body.segments,
        vault_news_dir=body.vault_news_dir,
    )
    return web_settings.read_settings()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
