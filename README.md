# NewsDigest · Tech News Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)

[中文](README.zh-CN.md) | **English**

> 📖 New to this? Read the beginner guide (Chinese): [INSTALL.md](INSTALL.md)

> Automatically collect the latest tech company news, classify & summarize it with an LLM, and archive it into your Obsidian vault — to help you analyze industry trends and discover niche opportunities.

## What it does

Runs a daily pipeline:

```
Collect (RSS + Hacker News) → Dedup → LLM classify + score → LLM summarize + insight → Archive to Obsidian
```

... with a local web UI for visualization and control.

## ✨ Features

- **Multi-source collection**: TechCrunch / The Verge / Ars Technica / Wired / MIT Technology Review (RSS) + Hacker News top stories
- **Smart classification**: the LLM judges relevance, classifies into 25 sub-domains across 6 groups, tags companies, and scores importance (1–5)
- **Chinese summaries**: each item gets a "summary" + "industry insight" + key points, with the original link
- **Obsidian archiving**: one note per news item (frontmatter + backlinks) + company/category/domain indexes + daily digest
- **Visual web UI**: one-click refresh, live progress, card-style news list
- **Flexible filtering**: item-count slider, importance threshold, domain checkboxes, near-duplicate removal
- **Multi-model**: DeepSeek / OpenAI / any OpenAI-compatible model — switch via config

## 📸 Screenshot

<!-- TODO: add a screenshot (e.g. docs/screenshot.png) and uncomment:
![NewsDigest UI](docs/screenshot.png)
-->

## 🚀 Quick start

### Requirements

- Python 3.12+

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

**① Copy `.env.example` to `.env`, and fill in your API key:**

```
LLM_API_KEY=your-key
```

**② Edit `config/config.yaml`:**

- `llm.model` / `llm.base_url`: model name and endpoint (defaults to DeepSeek; change these two + key to use OpenAI, etc.)
- `vault.news_dir`: set it to **your own Obsidian vault path**
- `fetch.max_items` / `filter.importance_min` / `filter.segments`: fetch limit and filtering rules

### 3. Run

```bash
python -m src.web.app
```

Open `http://127.0.0.1:8000` in your browser and click **Refresh**.

Or run the whole pipeline from the command line:

```bash
python -m src.scheduler.run
```

## 📁 Project layout

```
src/            # collect / classify / summarize / archive / web backend
static/         # web frontend page
config/         # configuration (model, sources, watchlist, taxonomy)
```

## ⚙️ Configuration

| File | Purpose |
|---|---|
| `config/config.yaml` | model, Obsidian path, fetch limit, filtering rules |
| `config/sources.yaml` | data sources (RSS + Hacker News) |
| `config/watchlist.yaml` | watchlist: sub-domain → companies |
| `config/taxonomy.yaml` | categories + sub-domain groups |

## 🧰 Tech stack

Python 3.12 · FastAPI · vanilla HTML/JS · OpenAI SDK (any OpenAI-compatible endpoint) · feedparser · httpx · trafilatura · PyYAML

## 📄 License

[MIT](LICENSE)
