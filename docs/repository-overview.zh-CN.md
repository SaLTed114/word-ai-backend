# 仓库详细介绍

## 项目定位

本仓库是 Word/WPS AI 写作助手项目的新后端原型。它从旧插件项目中拆出后端能力，先用 REPL 和 HTTP API 验证模型调用、prompt 设计、上下文输入、结构化响应和 agent 交互，再考虑前端 UI、Word 插件或 WPS 插件集成。

这样做的目标是减少调试复杂度：先确认“文本处理能力”本身可靠，再把它接入不同的用户界面。

## 当前阶段

当前阶段是后端原型阶段，已经完成：

- 通过 `.env` 读取模型配置
- 支持上海科技大学 GenAI 网关的 direct endpoint
- 支持标准 OpenAI SDK 风格配置的预留入口
- 提供 REPL 调试入口
- 提供 FastAPI HTTP API
- 支持 `syntax`、`word`、`style`、`agent` 四类命令
- 将 prompt 从代码中拆出到 `prompts/`
- 使用统一的 `TaskResponse` 返回结构化结果
- 将业务逻辑抽到 `app/services.py`，供 REPL 和 HTTP API 共用
- 提供后端维护的 agent session，并用本地 SQLite 保存消息历史
- 提供无框架静态 TXT 编辑器 demo，用于验证前后端数据流

暂未完成：

- 前端页面
- Word/WPS 插件壳子
- 自动化测试
- 一键安装程序

## 目录结构

```text
word-ai-backend/
├─ app/
│  ├─ __init__.py
│  ├─ ai_client.py
│  ├─ config.py
│  ├─ main.py
│  ├─ models.py
│  ├─ prompts.py
│  ├─ api_cli.py
│  ├─ repl.py
│  ├─ services.py
│  └─ storage.py
├─ prompts/
│  ├─ agent.md
│  ├─ style.md
│  ├─ syntax.md
│  └─ word_choice.md
├─ scripts/
│  └─ start_demo.ps1
├─ legacy/
│  └─ old_backend/
├─ docs/
├─ examples/
│  └─ simple-web/
│     ├─ app.js
│     ├─ index.html
│     └─ style.css
├─ .env.example
├─ .gitignore
├─ README.md
└─ requirements.txt
```

## 核心模块说明

### `app/config.py`

负责读取本地配置。默认会从项目根目录的 `.env` 中读取：

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_BASE_URL`
- `OPENAI_API_ENDPOINT`
- `OPENAI_PROXY_URL`
- `OPENAI_TRUST_ENV`
- `OPENAI_USE_JSON_MODE`

其中 `OPENAI_API_ENDPOINT` 用于学校 GenAI 网关这种直接请求地址；`OPENAI_TRUST_ENV=false` 用于避免 `httpx` 自动读取系统代理环境变量。

### `app/ai_client.py`

负责模型调用和响应解析。

当前支持两种模式：

- 标准 OpenAI SDK 模式：使用 `OPENAI_BASE_URL`
- direct endpoint 模式：使用 `OPENAI_API_ENDPOINT`

模型输出会被解析为统一的 Pydantic 模型。如果模型没有返回合法 JSON，会抛出清晰的错误，方便后续调试 prompt 或网关兼容性。

### `app/models.py`

定义统一的数据结构。

核心响应模型是 `TaskResponse`：

- `task`：任务类型，例如 `syntax`、`style`、`agent`
- `reply`：给用户看的简短回复
- `summary`：结果摘要
- `actions`：可被 UI 预览、确认和应用的操作建议
- `final_text`：完整改写后的文本

其中 `actions` 是后续前端集成的关键。当前使用 v2 动作结构，包含：

- `id`：动作编号
- `type`：动作类型，例如 `replace_selection`、`replace_range`、`add_comment`、`ask_user`
- `target`：作用位置，例如选区、范围、段落、章节、全文或光标位置
- `original` / `replacement`：修改前后文本
- `preview`：给用户确认用的前后预览
- `reason`：为什么建议这个动作
- `risk_level`：动作风险等级
- `requires_confirmation`：应用前是否必须确认

前端或 Word 插件应把 `actions` 当作“建议动作”，不要把修改类 action 直接静默写入文档。尤其是 `target.scope=document` 或 `risk_level=high` 的动作，必须显式确认。

agent session API 使用以下模型：

- `AgentSession`：一个后端维护的会话
- `AgentSessionMessage`：会话中的单条消息
- `AgentSessionTurnRequest`：向会话发送一轮用户输入
- `AgentSessionTurnResponse`：一轮 agent 回复以及对应的结构化结果

### `app/prompts.py`

负责加载 prompt 文件，并把用户选中文本、上下文、目标风格和输出格式约束组合成最终 prompt。

当前所有任务都共享一个结构化 JSON 输出约束，便于 REPL、HTTP API 和未来 UI 使用同一套响应格式。

### `app/services.py`

业务服务层。REPL 和 HTTP API 都调用这里的函数：

- `run_syntax`
- `run_word_choice`
- `run_style`
- `run_agent`

这一层负责把请求模型转换为 prompt，并调用 `AIClient` 得到 `TaskResponse`。后续如果要改 prompt、响应结构或任务逻辑，应优先在这一层调整，而不是让 REPL 和 HTTP API 各自维护一套逻辑。

### `app/storage.py`

负责 agent session 的本地持久化。当前使用 Python 标准库 `sqlite3`，默认数据库路径是：

```text
data/word_ai.sqlite3
```

这个数据库用于保存：

- agent 会话
- 用户消息
- assistant 消息
- assistant 返回的 `TaskResponse`

`data/` 已经被 `.gitignore` 忽略，不会把本地会话历史提交到仓库。

### `app/repl.py`

命令行调试入口。运行方式：

```powershell
python -m app.repl
```

支持命令：

- `config`
- `syntax`
- `word`
- `style`
- `agent`
- `help`
- `exit`

REPL 的意义是绕开 Word/WPS 插件环境，先快速验证后端能力。

REPL 当前只负责读取用户输入和打印结果，具体业务逻辑走 `app/services.py`。

### `app/api_cli.py`

HTTP API 调试入口。运行方式：

```powershell
python -m app.api_cli
```

它和 `app/repl.py` 的区别是：`api_cli` 不直接调用服务层，而是向正在运行的 FastAPI 服务发送真实 HTTP 请求。这样可以避免在 PowerShell 中手写 JSON，也可以更接近未来 CLI、前端或 Word 插件会使用的接口链路。

常用命令：

- `health`
- `syntax`
- `word`
- `style`
- `agent`
- `sessions`
- `messages <session_id>`

其中 `agent` 命令会创建后端 session，然后通过 `/agent/sessions/{session_id}/messages` 发送消息。

### `app/main.py`

FastAPI HTTP 服务入口。运行方式：

```powershell
uvicorn app.main:app --reload
```

启动后可访问：

```text
http://127.0.0.1:8000/docs
```

当前接口：

- `GET /health`
- `POST /tasks/syntax`
- `POST /tasks/word-choice`
- `POST /tasks/style`
- `POST /agent/sessions`
- `GET /agent/sessions`
- `GET /agent/sessions/{session_id}`
- `DELETE /agent/sessions/{session_id}`
- `GET /agent/sessions/{session_id}/messages`
- `POST /agent/sessions/{session_id}/messages`

### `prompts/`

存放外置 prompt 模板。

- `syntax.md`：语法检查
- `word_choice.md`：用词检查
- `style.md`：文风改写
- `agent.md`：多轮写作助手

后续可以加入 prompt 管理 API，让 UI 支持自定义系统 prompt。

### `legacy/`

存放旧项目后端代码，仅作为参考。新开发不应从 `legacy/` 中导入模块。

### `examples/simple-web/`

一个不依赖 Node.js 或前端框架的静态网页 demo。它模拟未来 Word/WPS 插件的核心数据流：

```text
编辑器文本或选区 -> fetch 调用 HTTP API -> 展示 TaskResponse -> 应用 final_text/action
```

当前能力：

- 作为 TXT 文本编辑器使用
- 打开和保存 `.txt`
- 根据选区或全文调用后端
- 调用 `syntax`、`word-choice`、`style`、`agent`
- 将 `final_text` 或 `replace_selection` 应用回文本框

这个 demo 的目的不是最终 UI，而是让前后端交互链路可视化。未来接入 Word/WPS 时，可以把 textarea 的读取和写回替换成文档 API，HTTP 调用逻辑保持基本不变。

### `scripts/start_demo.ps1` 与 `scripts/start_demo.bat`

`start_demo.ps1` 是 Windows PowerShell 一键启动脚本。它会：

- 检查当前 Python 环境是否安装了必要依赖
- 提醒 `.env` 是否存在
- 在新的 PowerShell 窗口中启动 `uvicorn app.main:app --reload`
- 打开 FastAPI 文档页 `http://127.0.0.1:8000/docs`
- 打开静态 TXT 编辑器 demo

`start_demo.bat` 是给双击启动准备的包装器。它会先尝试激活 `wordplugin` conda 环境，再调用 `start_demo.ps1`。如果环境名不同，可以修改 bat 文件中的 `CONDA_ENV`。

它不负责安装依赖，也不会写入 API key。推荐首次使用前创建独立 conda 环境：

```powershell
conda create -n wordplugin python=3.11
conda activate wordplugin
pip install -r requirements.txt
```

如果使用其他环境名，需要同步修改 `scripts/start_demo.bat`：

```bat
set "CONDA_ENV=wordplugin"
```

若不使用 bat，也可以在已经激活的环境中手动启动：

```powershell
uvicorn app.main:app --reload
```

## Agent 模式说明

当前 agent 模式是“带选区上下文的轻量多轮写作助手”，不是完整工具调用型 agent。

它的输入由三部分组成：

- 用户当前消息
- 可选的选中文本与上下文
- 可选的历史消息

REPL 中通过 `/text` 附加选中文本。每次模型回复后，REPL 会把用户消息和 assistant 回复追加到本轮历史里。

HTTP API 中的正式 agent 调用方式是 `/agent/sessions` 系列接口。它的基本流程是：

```text
POST /agent/sessions
-> 得到 session_id
-> POST /agent/sessions/{session_id}/messages
-> 后端读取历史、调用模型、保存用户消息和 assistant 回复
```

agent 返回统一的 `TaskResponse`：

- `reply` 用于聊天窗口展示
- `summary` 用于摘要展示
- `final_text` 用于完整预览
- `actions` 用于前端渲染预览、确认和“应用修改”等按钮

## 推荐开发路线

### 第一阶段：稳定 REPL 与 HTTP API 原型

目标：

- 调整 response schema
- 验证更多模型
- 增强错误处理
- 增强上下文输入
- 梳理 agent 对话行为

### 第二阶段：完善 API 能力

建议新增或完善：

- `GET /prompts`
- `PUT /prompts/{name}`
- session 化 agent 历史
- 更稳定的错误响应格式
- 自动化测试

### 第三阶段：前端或插件集成

后端稳定后，可以选择不同壳子：

- 当前静态 TXT 编辑器 demo
- 普通 Web 前端
- Microsoft Word Office Add-in
- WPS 插件机制
- 本地桌面应用

无论 UI 形式如何，都应复用同一套后端 API 和 response schema。

### 第四阶段：安装与部署

为“一键安装程序”做准备：

- 固定依赖版本
- 补充启动脚本
- 加 `.env.example`
- 加健康检查
- 后续考虑 PyInstaller 或安装向导

## 安全与协作规范

- 不要提交 `.env`
- 不要提交真实 API key
- 不要在 README、截图或聊天记录中暴露密钥
- 新 prompt 应放入 `prompts/`
- 新接口应复用 `TaskResponse` 或其后续演化版本
- `legacy/` 只作参考，不作为新代码依赖
