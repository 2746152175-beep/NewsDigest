"""R5-a FastAPI backend for the news agent."""

import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.config_loader import load_config, resolve_path
from src.web import settings as web_settings
from src.web.runner import runner

INDEX_PATH = Path(__file__).resolve().parent.parent.parent / "static" / "index.html"

app = FastAPI(title="News Agent", version="R5-b")


class SettingsBody(BaseModel):
    model: str
    base_url: str
    api_key: str
    max_items: int | None = None
    importance_min: int | None = None
    segments: list[str] | None = None


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    if not INDEX_PATH.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return HTMLResponse(INDEX_PATH.read_text(encoding="utf-8"))


@app.post("/api/refresh")
def refresh() -> dict:
    task_id = runner.start()
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
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="summarized file is invalid") from exc
    if not isinstance(payload, list):
        raise HTTPException(status_code=500, detail="summarized file is not a list")
    return payload


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
    )
    return web_settings.read_settings()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
