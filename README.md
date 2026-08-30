# NewsDigest · 科技新闻智能体

> 自动采集科技公司最新动态，经 LLM 智能筛选、分类、概括总结，归档进你的 Obsidian 笔记库，助你分析产业趋势、发现行业细分领域。

## 它能做什么

每天自动完成一条流水线：

```
采集(RSS + Hacker News) → 去重 → LLM 筛选+分类+打分 → LLM 概括+产业启示 → 归档 Obsidian
```

并通过本地 Web 界面可视化操作。

## ✨ 功能特性

- **多源采集**：TechCrunch / The Verge / Ars Technica / Wired / MIT Tech Review 五大 RSS + Hacker News 热门
- **智能分类**：LLM 自动判断相关性，归类到 6 大组 25 个细分领域，标注公司与重要性（1–5）
- **中文概括**：每条新闻生成「内容概括」+「产业启示」+ 要点列表，附原文链接
- **归档 Obsidian**：一条新闻一个笔记（frontmatter + 双向链接）+ 公司/分类/领域索引 + 每日简报
- **Web 可视化**：点「刷新」触发流水线、实时进度、新闻卡片展示
- **灵活过滤**：数量滑块、重要性阈值、领域勾选、相似新闻去重
- **多模型**：DeepSeek / OpenAI / 任意 OpenAI 兼容模型，改配置即切换

## 🚀 快速开始

### 环境要求

- Python 3.12+

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

**① 复制 `.env.example` 为 `.env`，填入你的 API Key：**

```
LLM_API_KEY=你的key
```

**② 编辑 `config/config.yaml`：**

- `llm.model` / `llm.base_url`：模型名与端点（默认 DeepSeek，换 OpenAI 改这两处 + key）
- `vault.news_dir`：改成**你自己的 Obsidian 仓库路径**
- `fetch.max_items` / `filter.importance_min` / `filter.segments`：抓取数量与过滤规则

### 3. 启动

```bash
python -m src.web.app
```

浏览器打开 `http://127.0.0.1:8000`，点「刷新」即可。

命令行一键跑全流程：

```bash
python -m src.scheduler.run
```

## 📁 目录结构

```
src/            # 采集 / 分类 / 概括 / 归档 / Web 后端
static/         # Web 前端页面
config/         # 配置（模型、数据源、观察清单、词表）
```

## ⚙️ 配置说明

| 文件 | 作用 |
|---|---|
| `config/config.yaml` | 模型、Obsidian 路径、抓取数量、过滤规则 |
| `config/sources.yaml` | 数据源（RSS + Hacker News） |
| `config/watchlist.yaml` | 观察清单：细分领域 → 公司列表 |
| `config/taxonomy.yaml` | 分类词表 + 细分领域分组 |

## 🧰 技术栈

Python 3.12 · FastAPI · 原生 HTML/JS · OpenAI SDK（兼容任意 OpenAI 端点）· feedparser · httpx · trafilatura · PyYAML

## 📄 License

[MIT](LICENSE)
