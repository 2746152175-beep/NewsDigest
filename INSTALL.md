# NewsDigest 小白安装指南（零基础版）

> 不用懂编程，跟着一步步做就能跑起来。本指南针对 Windows（Win10/11）。

## 你需要提前准备 2 样东西

1. **一个 LLM 的 API Key**（DeepSeek 或 OpenAI，获取方式见下方第四步）
2. 一台能联网的电脑

---

## 第一步：安装 Python 3.12

1. 浏览器打开 👉 https://www.python.org/downloads/
2. 点黄色按钮 **Download Python 3.12.x**
3. 双击下载好的安装包
4. ⚠️ **最关键一步**：安装界面**最下面勾选 `Add Python to PATH`**（很多人漏了这步）
5. 点 **Install Now**，等它装完

**验证是否成功**：按键盘 `Win` 键，输入 `cmd` 回车，在弹出的黑窗口里输入：

```
python --version
```

回车后显示 `Python 3.12.x` 就成功了。

> 如果显示「'python' 不是内部或外部命令」，就是第 4 步没勾选，卸载重装一遍、记得勾上。

---

## 第二步：下载项目

**方式 A（会 git 的人）**：在黑窗口里输入：

```
git clone https://github.com/2746152175-beep/NewsDigest.git
```

**方式 B（推荐小白，直接下载压缩包）**：

1. 浏览器打开 👉 https://github.com/2746152175-beep/NewsDigest
2. 点绿色按钮 **Code** → **Download ZIP**
3. 下载后**解压**到你想放的位置（比如 `D:\NewsDigest`）

---

## 第三步：安装依赖

1. 打开解压后的 **NewsDigest** 文件夹
2. 点文件夹上方的**地址栏**，输入 `cmd` 回车（会在当前文件夹打开黑窗口）
3. 在黑窗口里输入：

```
pip install -r requirements.txt
```

回车，等它下载安装，最后看到 `Successfully installed ...` 就完成了。

> 如果 `pip` 报错，换这个命令再试：
> ```
> python -m pip install -r requirements.txt
> ```

---

## 第四步：配置（填 key + 改路径）

### 4.1 先拿到你的 API Key

- **DeepSeek**：打开 https://platform.deepseek.com → 注册登录 → 左侧「API Keys」→ 创建 → 复制那串 `sk-` 开头的 key
- **OpenAI**：打开 https://platform.openai.com → 注册登录 → API Keys → 创建 → 复制

### 4.2 把 key 填进项目

1. 在 NewsDigest 文件夹里找到 `.env.example` 文件
2. **复制一份**，把复制出来的重命名为 `.env`（注意：就是「.env」，没有后缀）
3. 用**记事本**打开 `.env`，把等号后面换成你的真实 key：

```
LLM_API_KEY=sk-你的真实key
```

保存关闭。

### 4.3 改模型和 Obsidian 路径

用记事本打开 `config/config.yaml`，改两处：

**① 模型**（找到这几行）：

```yaml
llm:
  model: "deepseek-v4-flash"              # 用 DeepSeek 就不用改
  base_url: "https://api.deepseek.com"    # 用 DeepSeek 就不用改
```

- 用 **DeepSeek**：默认就行，跳过这步
- 用 **OpenAI**：把 `model` 改成 `"gpt-4o"`、`base_url` 改成 `"https://api.openai.com/v1"`

**② Obsidian 路径**（找到这一行）：

```yaml
vault:
  news_dir: "改成你的Obsidian仓库路径"   # 改成你自己的 Obsidian 仓库路径
```

把引号里的内容改成**你自己的 Obsidian 仓库路径**。比如你的 Obsidian 笔记在 `D:\我的知识库`，就写：

```yaml
  news_dir: "D:/我的知识库/新闻记忆库"
```

（注意斜杠方向用 `/`，最后 `新闻记忆库` 是想存放新闻的子文件夹名，可自取）

---

## 第五步：启动

在项目文件夹的黑窗口里输入：

```
python -m src.web.app
```

回车后，看到下面这行就说明成功了：

```
Uvicorn running on http://127.0.0.1:8000
```

然后**浏览器打开** 👉 http://127.0.0.1:8000

> ⚠️ 那个黑窗口**别关**，关了服务就停了。

---

## 第六步：使用

1. 浏览器里点 **「刷新」** 按钮
2. 等几分钟（它在调 LLM 抓取+分类+概括）
3. 新闻就显示出来了，同时自动归档进你的 Obsidian

---

## 常见问题

| 现象 | 解决 |
|---|---|
| `python 不是内部命令` | 装 Python 时没勾 `Add to PATH`，重装 |
| `pip` 报中文乱码/路径错误 | 用 `python -m pip install -r requirements.txt` |
| 刷新后没反应/报错 | 看黑窗口里的报错，多半是 key 或模型名填错了 |
| Obsidian 里没有笔记 | 检查 `config.yaml` 的 `news_dir` 路径写对没 |
| 想每天自动跑 | 用 `run_daily.bat`（Windows 任务计划程序，见 README） |

---

搞定！如果你卡在哪一步，把黑窗口里的报错截图发出来，就能帮你定位。
