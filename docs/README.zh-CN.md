# Word AI Backend

这是一个面向 Word/WPS AI 写作助手的干净后端原型。

当前仓库优先通过 FastAPI HTTP API 和一个轻量 HTTP CLI 验证后端能力，暂时不绑定具体前端、Word 插件或 WPS 插件壳子。

## 文档

- [详细仓库介绍](repository-overview.zh-CN.md)
- [返回英文 README](../README.md)

## 当前功能

- 语法检查
- 用词检查
- 文风改写
- 公式 / 方程处理（LaTeX、OMML）
- Agent 式多轮写作辅助
- Subagent 分发机制，支持专项编辑任务（校对、学术润色、摘要、翻译、公式及自定义 subagent）
- LLM 自动规划 subagent 调度
- LLM 合并多个 subagent 结果
- 后端维护的 agent session，并用本地 SQLite 保存消息
- session memory，用于保存文档摘要、写作目标、术语和用户偏好
- 后端 context builder，用于把全文、选区和作用范围整理成模型输入
- FastAPI HTTP 接口
- 外置 prompt 模板
- Skill 管理 API（markdown skill 文件的增删改查）
- 支持上海科技大学 GenAI 网关 direct endpoint 调用方式

## 快速开始

1. 创建并激活推荐的 conda 环境：

```powershell
conda create -n wordplugin python=3.11
conda activate wordplugin
```

2. 安装依赖：

```powershell
pip install -r requirements.txt
```

3. 复制 `.env.example` 为 `.env`，并填写你自己的 API 配置：

```env
OPENAI_API_KEY=
OPENAI_MODEL=GPT-5.4
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_ENDPOINT=https://genaiapi.shanghaitech.edu.cn/api/v1/start
OPENAI_PROXY_URL=
OPENAI_TRUST_ENV=false
OPENAI_USE_JSON_MODE=true
```

4. 启动 HTTP API：

```powershell
uvicorn app.main:app --reload
```

然后打开：

```text
http://127.0.0.1:8000/docs
```

5. 另开一个终端使用 HTTP CLI：

```powershell
python -m app.api_cli
```

HTTP CLI 会真实请求正在运行的后端，并把 `reply`、`final_text`、`actions` 排版输出；这样就不需要在 PowerShell 里手写 JSON。

## HTTP CLI

先启动后端：

```powershell
uvicorn app.main:app --reload
```

然后运行：

```powershell
python -m app.api_cli
```

可用命令：

- `health`：检查后端状态
- `syntax`：调用 `POST /tasks/syntax`
- `word`：调用 `POST /tasks/word-choice`
- `style`：调用 `POST /tasks/style`
- `context`：预览 `POST /context/build`
- `agent`：创建 agent session，并通过 `POST /agent/sessions/{session_id}/messages` 对话
- `sessions`：列出最近的 agent session
- `messages <id>`：查看某个 session 里的消息
- `memory <id>`：查看某个 session 的记忆
- `set-memory <id>`：交互式替换某个 session 的记忆
- `skills`：列出可用的 skill 文件

进入 `agent` 模式后：

- `/context`：附加文档全文、选中文本和作用范围，供后续对话使用
- `/clear-context`：清除已附加的文档上下文
- `/memory`：查看当前 session 记忆
- `/set-memory`：替换当前 session 记忆
- `/messages`：查看当前 session 消息
- `/subagents <name,...>`：将当前消息分发给一个或多个 subagent（例如 `/subagents proofread,academic_polish`）
- `/plan`：请求 LLM planner 为当前任务推荐合适的 subagent
- `/new`：创建新 session
- `/exit`：退出 agent 模式

如果后端不在默认地址，可以指定：

```powershell
python -m app.api_cli --base-url http://127.0.0.1:8000
```

## Agent 流程测试

先启动后端：

```powershell
uvicorn app.main:app --reload
```

然后运行固定 agent 流程测试：

```powershell
python .\scripts\test_agent_flow.py
```

如果只想测试后端链路、不真实调用模型，可以运行：

```powershell
python .\scripts\test_agent_flow.py --mock
```

这个脚本会测试：

- `GET /health`
- `POST /context/build`
- `POST /agent/sessions`
- `PUT /agent/sessions/{session_id}/memory`
- `POST /agent/sessions/{session_id}/messages`
- `GET /agent/sessions/{session_id}/messages`
- `DELETE /agent/sessions/{session_id}`

它使用固定的方法部分段落，设置 session memory，发送中文 agent 指令，并检查 agent 返回是否包含结构化结果。

## Agent 场景测试

运行默认多轮场景：

```powershell
python .\scripts\agent_scenario_test.py
```

如果不想真实调用模型，可以运行：

```powershell
python .\scripts\agent_scenario_test.py --mock
```

默认场景文件在：

```text
tests/scenarios/academic_rewrite.zh-CN.json
```

场景文件可以定义 session memory、document context、多轮用户消息，以及轻量 expect 检查，例如是否需要 actions、final_text、消息数量和 action schema。

## 网页 Agent Demo

先启动后端：

```powershell
uvicorn app.main:app --reload
```

然后打开：

```text
examples/simple-web/index.html
```

这个 demo 左侧是文档编辑器，右侧是 agent 对话面板。它调用 session-based agent API，发送 `document_context`，并支持在对话前保存 session memory。

## HTTP API

- `GET /health`：检查服务状态和 AI 配置状态
- `GET /settings/ai-config`：查看当前 AI 配置
- `PUT /settings/ai-config`：运行时更新 AI 配置
- `POST /tasks/syntax`：检查语法、拼写、标点和表达清晰度
- `POST /tasks/word-choice`：检查用词和短语表达
- `POST /tasks/style`：将文本改写为目标文风
- `POST /tasks/formula`：处理 LaTeX、公式和 Word 公式输出
- `POST /context/build`：将文档全文和选区信息转换成模型可用的 `TextRequest`
- `POST /agent/sessions`：创建一个由后端维护历史的 agent 会话
- `GET /agent/sessions`：列出最近的 agent 会话
- `GET /agent/sessions/{session_id}`：查看单个 agent 会话
- `DELETE /agent/sessions/{session_id}`：删除单个 agent 会话
- `GET /agent/sessions/{session_id}/messages`：列出会话内消息
- `GET /agent/sessions/{session_id}/memory`：查看会话记忆
- `PUT /agent/sessions/{session_id}/memory`：替换会话记忆
- `POST /agent/sessions/{session_id}/messages`：向会话发送一条用户消息，并得到一轮 assistant 回复（支持通过 `subagents`、`auto_subagents` 或 `planned_subagents` 字段进行 subagent 分发）
- `POST /agent/sessions/{session_id}/subagents/plan`：请求 LLM planner 为任务推荐 subagent 调用
- `POST /agent/sessions/{session_id}/subagents/run`：独立运行单个 subagent（分步模式）
- `POST /agent/sessions/{session_id}/subagents/merge`：合并 subagent 结果并持久化消息（分步模式）
- `GET /skills`：列出可用的 skill 文件
- `GET /skills/{name}`：读取 skill 文件内容
- `POST /skills`：创建新 skill 文件
- `PUT /skills/{name}`：更新或重命名 skill 文件
- `DELETE /skills/{name}`：删除 skill 文件

`POST /tasks/syntax` 请求示例：

```json
{
  "text": "He dont know what to did yesterday.",
  "context": {
    "before": "",
    "after": ""
  },
  "instruction": ""
}
```

## 架构说明

HTTP API 调用共享服务层：

```text
HTTP API -> app.services -> app.ai_client -> 模型网关
```

当前 agent 模式是一个轻量多轮写作助手。它可以使用选中文本、可选上下文和后端维护的对话历史，并返回用户可读回复以及结构化修改动作。

session API 会把对话历史保存在本地 SQLite 数据库 `data/word_ai.sqlite3` 中；该目录已被 `.gitignore` 忽略。

session memory 也保存在 SQLite 中。每个 session 可以保存：

- `document_summary`：文档摘要
- `writing_goals`：写作目标
- `key_terms`：关键术语
- `user_preferences`：用户偏好

每次 agent 回复都会自动把这些记忆注入 prompt。v1 中 memory 是显式更新的：客户端或 CLI 通过 `PUT /agent/sessions/{session_id}/memory` 修改，模型暂时不会自己改写 memory。

context builder 接受文档级输入：

- `document_text`：从文档中取得的纯文本
- `selection.text` 或 `selection.start` / `selection.end`：当前用户选区
- `active_scope`：作用范围，可为 `selection`、`paragraph`、`section`、`document`
- `context_window_chars`：选区前后各保留多少上下文

它会返回标准化后的 `TextRequest`，包含要发送给模型的文本以及 before/after 上下文。`before` 和 `after` 会继续保留，作为内部模型输入格式；新的客户端通常应该传 `document_context`，让后端自动填充这些字段。

`actions` 现在使用 v2 动作结构。每个 action 包含：

- `id`：用于预览和后续应用的稳定编号
- `type`：建议操作，例如 `replace_selection`、`replace_range`、`add_comment`、`ask_user`
- `target`：动作要作用的位置
- `preview`：应用前后的文本预览
- `risk_level`：风险等级，可能是 `info`、`low`、`medium`、`high`
- `requires_confirmation`：前端或插件在应用前是否必须让用户确认

客户端应把 actions 当作”建议动作”，而不是直接执行的命令。会修改文档内容的 action 应先展示预览并等待用户确认。

## Subagent 机制

Agent 支持将用户请求分发给多个专门的 subagent，每个 subagent 聚焦于一个编辑领域。相比单一 prompt，这种方式能更好地处理多面任务（例如”校对并润色这一段”）。

### 预设 Subagent

| 名称 | Skill 文件 | 描述 |
|------|-----------|------|
| `proofread` | `skills/proofread.md` | 语法、拼写、标点、表达清晰度 |
| `academic_polish` | `skills/academic-polish.md` | 正式学术英语润色 |
| `summarize` | `skills/summarize.md` | 简洁摘要 |
| `translate_zh` | `skills/translate-zh.md` | 中英互译 |
| `formula` | `skills/formula.md` | LaTeX、公式、Word 公式输出 |

每个预设 subagent 包含：
- **skill 文件**：注入 prompt 的领域专用指令
- **允许的操作类型**：限制其可返回的编辑动作
- **上下文模式**：控制包含多少周围文本

也支持自定义 subagent 名称（不在预设注册表中）—— 它们会以通用写作助手 prompt 和调用者提供的指令运行。

### 分发模式

通过 `POST /agent/sessions/{session_id}/messages` 调用 subagent 有三种方式：

1. **显式列表**（`subagents` 字段）：提供预设或自定义 subagent 名称列表。
   ```json
   { “message”: “检查语法并提高学术性。”, “subagents”: [“proofread”, “academic_polish”] }
   ```

2. **自动规划**（`auto_subagents: true`）：后端调用 LLM planner 决定需要哪些 subagent（如果有的话）。planner 会看到可用预设名称、skill 文件、选中文本和用户消息，返回最多 3 个带自定义指令的 subagent 调用。
   ```json
   { “message”: “让这段文字更清晰、更正式。”, “auto_subagents”: true }
   ```

3. **预规划**（`planned_subagents` 字段）：客户端先调用 `POST /agent/sessions/{session_id}/subagents/plan`，审核计划后再发送批准的调用。
   ```json
   { “message”: “...”, “planned_subagents”: [{“name”: “proofread”, “instruction”: “只关注语法。”}] }
   ```

### 分步模式

对于需要精细控制的客户端，subagent 流程可以拆分为显式步骤：

1. `POST /agent/sessions/{session_id}/subagents/run` — 运行单个 subagent，获取其 `TaskResponse`，不持久化消息
2. `POST /agent/sessions/{session_id}/subagents/merge` — 合并一个或多个 `run` 调用的结果，持久化用户和 assistant 消息，并可选运行 LLM 合并

这允许客户端在合并前检查或修改单个 subagent 的响应。

### LLM 合并

Subagent 运行后，它们的 `TaskResponse` 结果通过拼接合并（replies 连接，actions 汇集，保留最后一个非空 `final_text`）。当 `llm_merge_subagents` 为 true（默认值）时，合并后的结果会经过一次额外的 LLM 调用，协调冲突并生成一个连贯的 `TaskResponse`。

### Skill 管理

Skills 是 `skills/` 目录下的 markdown 文件，包含领域专用的 prompt 指令。`/skills` CRUD API 允许客户端在运行时列出、读取、创建、更新和删除 skill 文件。预设 subagent 各自有默认 skill 文件；自定义 skill 可以通过 `skills` 字段按轮次传入，并注入到 subagent prompt 中。

通过 HTTP CLI 进行最小 session 调用：

```text
word-ai-http> agent
Session title [cli]: demo
agent> /context
Document title (optional):
Enter document text. Finish with a line containing only EOF.
Tip: paste the full text when available; paste only selected text if not.
This method is good and useful.
EOF
Active scope [selection/paragraph/section/document]:
Enter selected text, or leave empty and type EOF to use offsets/full document.
This method is good and useful.
EOF
Selection start offset (optional, for exact document positions):
Selection end offset (optional, for exact document positions):
Instruction (optional):
agent> 解释这句话的问题，并给一个更正式的版本。
```

## 安全提醒

不要提交 `.env` 或任何真实 API key。真实密钥只应保存在本地。
