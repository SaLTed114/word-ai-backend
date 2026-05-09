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

暂未完成：

- 前端页面
- Word/WPS 插件壳子
- 持久化会话
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
│  ├─ repl.py
│  └─ services.py
├─ prompts/
│  ├─ agent.md
│  ├─ style.md
│  ├─ syntax.md
│  └─ word_choice.md
├─ legacy/
│  └─ old_backend/
├─ docs/
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
- `actions`：可被 UI 应用的操作建议
- `final_text`：完整改写后的文本

其中 `actions` 是后续前端集成的关键。前端可以把 `replace_selection` 渲染成“应用修改”按钮。

`AgentChatRequest` 用于 agent HTTP 接口，包含：

- `message`：用户本轮消息
- `selection`：当前选中文本和上下文，可为空
- `history`：前端或 REPL 保存的对话历史

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
- `POST /agent/chat`

### `prompts/`

存放外置 prompt 模板。

- `syntax.md`：语法检查
- `word_choice.md`：用词检查
- `style.md`：文风改写
- `agent.md`：多轮写作助手

后续可以加入 prompt 管理 API，让 UI 支持自定义系统 prompt。

### `legacy/`

存放旧项目后端代码，仅作为参考。新开发不应从 `legacy/` 中导入模块。

## Agent 模式说明

当前 agent 模式是“带选区上下文的轻量多轮写作助手”，不是完整工具调用型 agent。

它的输入由三部分组成：

- 用户当前消息
- 可选的选中文本与上下文
- 可选的历史消息

REPL 中通过 `/text` 附加选中文本。每次模型回复后，REPL 会把用户消息和 assistant 回复追加到本轮历史里。HTTP API 中，前端需要自己维护 `history` 并传给 `/agent/chat`。

agent 返回统一的 `TaskResponse`：

- `reply` 用于聊天窗口展示
- `summary` 用于摘要展示
- `final_text` 用于完整预览
- `actions` 用于前端渲染“应用修改”等按钮

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
