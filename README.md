# 新闻智能体

每日自动采集美国优秀科技公司的最新消息、技术突破与前瞻布局，经 LLM 筛选分类、概括总结后，归档进 Obsidian 新闻记忆库，用于产业趋势分析与行业细分领域发现。

## 已锁定决策

| 决策点 | 结论 |
|---|---|
| 聚焦范围 | 全领域科技公司 |
| LLM 引擎 | DeepSeek V4 Flash（OpenAI 兼容接口） |
| 数据源 | 轻量聚合：RSS + Hacker News API |
| 存储结构 | 一条新闻一个 note + 双向链接 |

## 架构

```
sources.yaml + watchlist.yaml（配置）
        │
        ▼
[RSS feedparser] ──┐
[HN API httpx]   ──┼──► 归一化 Item ──► 去重(SQLite) ──► 原始 JSON
                    │                                        │
                    ▼                                        ▼
                              [DeepSeek 筛选+分类] R1
                              [DeepSeek 概括+总结] R2
                                        │
                                        ▼
                              [写入 Obsidian] R3
                                        │
                                        ▼
                              索引/MOC + 每日简报
```

## 目录结构

```
新闻智能体/
├── src/
│   ├── fetch/        # R0 采集器（rss / hn / normalize）
│   ├── classify/     # R1 筛选+分类（DeepSeek）
│   ├── summarize/    # R2 概括+总结（DeepSeek）
│   ├── write/        # R3 归档写入（note / index / digest）
│   └── scheduler/    # R4 调度（dedup / run / log）
├── config/
│   ├── config.yaml   # 总配置（vault 路径、DeepSeek）
│   ├── sources.yaml  # 数据源清单
│   ├── watchlist.yaml# 观察清单（公司）
│   └── taxonomy.yaml # 分类 + 细分领域词表
├── data/             # 中间产物（raw / classified / summarized）
├── state/seen.db     # SQLite 去重库
├── logs/
└── tests/
```

Obsidian 记忆库产出目录：`D:\知识库\仓库\新闻记忆库\`

## 分轮路线

- **R0 地基**：采集 + 归一化 + 去重（输出 `data/raw/*.json`）
- **R1 智能筛选分类**：LLM 判断相关性 + 归类（输出 `data/classified/*.json`）
- **R2 概括总结**：内容概括 + 产业启示（输出 `data/summarized/*.json`）
- **R3 Obsidian 归档**：写入 vault + 索引 + 每日简报
- **R4 调度与增量**：定时 + 日志 + 容错

## 快速开始

1. **配置密钥**：复制 `.env.example` 为 `.env`，填入你的 API Key（DeepSeek / OpenAI 等皆可，`.env` 已被 gitignore，不会泄露）。
2. **（可选）改模型**：编辑 `config/config.yaml` 的 `llm.model` / `llm.base_url`。
3. **安装依赖**：`pip install -r requirements.txt`
4. **跑通全流程**：`python -m src.scheduler.run`

## 每日定时

项目根目录已提供 `run_daily.bat`，它会在运行时 `cd /d` 到 `D:\工作区\新闻智能体`，
调用 `D:\工作区\软件\Python312\python.exe -m src.scheduler.run`（密钥从 `.env` 读取），
并将输出追加到 `D:\工作区\新闻智能体\logs\run_daily.log`。

首次使用前，请复制 `.env.example` 为 `.env` 并填入你的 `LLM_API_KEY`；
模型名与端点按需在 `config/config.yaml` 的 `llm.model` / `llm.base_url` 修改。

Windows 任务计划程序每天 07:30 执行的示例：

```bat
schtasks /create /tn "NewsAgentDaily" /tr "D:\工作区\新闻智能体\run_daily.bat" /sc daily /st 07:30 /f
```

任务、脚本、工作目录和日志均在 D 盘。查看或删除任务：

```bat
schtasks /query /tn "NewsAgentDaily" /v /fo LIST
schtasks /delete /tn "NewsAgentDaily" /f
```

## Web 前端

项目根目录已提供 `start_web.bat`，双击即可启动本地 Web 服务并自动打开浏览器：

```bat
start_web.bat
```

访问地址：`http://127.0.0.1:8000`（仅绑定本机）。

页面包含三块：

- 顶部：选择日期、「刷新」按钮与流水线进度（R0 采集 / R1 分类 / R2 概括 / R3 归档）。
- 主体：当天新闻列表，按分类分组展示概括、产业启示、要点与原文链接。
- 设置面板：可切换模型（`deepseek-v4-flash` / `deepseek-v4-pro`）、修改 `base_url` 与 API Key；保存后模型写入 `config/config.yaml`，Key 写入 `.env`，下次刷新生效。

## 注意

- `config.yaml` 中的 `llm.model` 需以账号实际可用模型名为准。
- 若使用自建/代理 DeepSeek 端点，改 `llm.base_url`。

## 工作约定

- **禁止写 C 盘**：所有代码、数据、日志、状态库、缓存都必须在 D 盘（本项目内或 D 盘其它目录），不得写入/占用 C 盘空间。
- **提示词自包含**：交付给 Codex 的每条提示词都自包含，可粘贴到 Codex 新对话直接继续，不依赖历史上下文。
