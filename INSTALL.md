# NewsDigest 小白安装指南（零基础版）

> 不用懂编程，跟着做就能跑。本指南针对 Windows（Win10/11）。
> **所有配置都能在网页里完成，不用手动改任何文件。**

## 第一步：安装 Python 3.12

1. 浏览器打开 👉 https://www.python.org/downloads/
2. 点黄色按钮 **Download Python 3.12.x**
3. 双击下载好的安装包
4. ⚠️ **最关键**：安装界面**最下面勾选 `Add Python to PATH`**（很多人漏了这步）
5. 点 **Install Now**，等它装完

**验证**：按键盘 `Win` 键，输入 `cmd` 回车，在黑窗口输入：

```
python --version
```

显示 `Python 3.12.x` 就成功了。若显示「不是内部或外部命令」，就是第 4 步没勾，重装一遍。

## 第二步：下载项目

- **方式 A（会 git 的）**：黑窗口输入 `git clone https://github.com/2746152175-beep/NewsDigest.git`
- **方式 B（小白推荐）**：打开 https://github.com/2746152175-beep/NewsDigest → 绿色 **Code** → **Download ZIP** → 解压到 D 盘

## 第三步：安装依赖

1. 打开 NewsDigest 文件夹，点上方**地址栏**输入 `cmd` 回车
2. 输入并回车：

```
pip install -r requirements.txt
```

等它下载，最后看到 `Successfully installed ...` 即可。

## 第四步：启动

黑窗口输入：

```
python -m src.web.app
```

看到 `Uvicorn running on http://127.0.0.1:8000` 后，浏览器打开 👉 http://127.0.0.1:8000

> ⚠️ 黑窗口别关，关了服务就停。

## 第五步：在网页里配置（不用碰文件）

先准备好你的 API Key（**二选一**）：

- **DeepSeek**：https://platform.deepseek.com → 注册登录 → API Keys → 创建，复制 `sk-` 开头的 key
- **OpenAI**：https://platform.openai.com → 注册登录 → API Keys → 创建，复制 key

然后回到网页，点右上角 **「设置」**，依次填：

| 项 | 怎么填 |
|---|---|
| **服务商** | DeepSeek 或 OpenAI |
| **模型** | 用 DeepSeek 默认不用改；用 OpenAI 填 `gpt-4o` |
| **base_url** | 选了服务商会自动填好 |
| **api_key** | 粘贴你的 key |
| **Obsidian 路径** | 你的 Obsidian 仓库路径，如 `D:/我的知识库/新闻记忆库` |
| 数量/重要性/领域 | 可选，默认就行 |

填完点 **「保存」**。

## 第六步：刷新

点 **「刷新」** → 等几分钟（在调 LLM）→ 新闻显示出来，同时自动归档进你的 Obsidian。

---

## 常见问题

| 现象 | 解决 |
|---|---|
| `python 不是内部命令` | 装 Python 时没勾 `Add to PATH`，重装 |
| `pip` 报中文乱码 | 用 `python -m pip install -r requirements.txt` |
| 刷新后报错 | 看黑窗口报错，多半是 key 或模型名填错 |
| Obsidian 里没笔记 | 检查设置里的「Obsidian 路径」写对没 |
| 想每天自动跑 | 用 `run_daily.bat` + Windows 任务计划（见 README） |

搞定！卡在哪一步，把黑窗口报错截图发出来即可。
