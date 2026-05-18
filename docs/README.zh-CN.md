# Word AI Backend

这是一个面向 Word/WPS AI 写作助手的干净后端原型。

当前仓库优先通过 REPL 和一个轻量 HTTP API 验证后端能力，暂时不绑定具体前端、Word 插件或 WPS 插件壳子。

## 文档

- [详细仓库介绍](repository-overview.zh-CN.md)
- [返回英文 README](../README.md)

## 当前功能

- 语法检查
- 用词检查
- 文风改写
- Agent 式多轮写作辅助
- 后端维护的 agent session，并用本地 SQLite 保存消息
- FastAPI HTTP 接口
- 外置 prompt 模板
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

4. 启动 REPL：

```powershell
python -m app.repl
```

5. 或者启动 HTTP API：

```powershell
uvicorn app.main:app --reload
```

然后打开：

```text
http://127.0.0.1:8000/docs
```

6. 或者在启动 HTTP API 后使用 HTTP CLI：

```powershell
python -m app.api_cli
```

HTTP CLI 会真实请求正在运行的后端，并把 `reply`、`final_text`、`actions` 排版输出；这样就不需要在 PowerShell 里手写 JSON。

7. 试用一个 REPL 命令：

```text
word-ai> syntax
Enter selected text. Finish with a line containing only EOF.
He dont know what to did yesterday.
EOF
```

## REPL 命令

- `config`：查看或更新模型配置
- `syntax`：检查语法、拼写、标点和表达清晰度
- `word`：检查用词和短语表达
- `style`：将文本改写为指定文风
- `agent`：进入多轮写作助手模式
- `help`：显示帮助
- `exit`：退出

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
- `agent`：创建 agent session，并通过 `POST /agent/sessions/{session_id}/messages` 对话
- `sessions`：列出最近的 agent session
- `messages <id>`：查看某个 session 里的消息

进入 `agent` 模式后：

- `/text`：附加选中文本，供后续对话使用
- `/clear-text`：清除已附加的选中文本
- `/messages`：查看当前 session 消息
- `/new`：创建新 session
- `/exit`：退出 agent 模式

如果后端不在默认地址，可以指定：

```powershell
python -m app.api_cli --base-url http://127.0.0.1:8000
```

## HTTP API

- `GET /health`：检查服务状态和 AI 配置状态
- `POST /tasks/syntax`：检查语法、拼写、标点和表达清晰度
- `POST /tasks/word-choice`：检查用词和短语表达
- `POST /tasks/style`：将文本改写为目标文风
- `POST /agent/sessions`：创建一个由后端维护历史的 agent 会话
- `GET /agent/sessions`：列出最近的 agent 会话
- `GET /agent/sessions/{session_id}`：查看单个 agent 会话
- `DELETE /agent/sessions/{session_id}`：删除单个 agent 会话
- `GET /agent/sessions/{session_id}/messages`：列出会话内消息
- `POST /agent/sessions/{session_id}/messages`：向会话发送一条用户消息，并得到一轮 assistant 回复

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

REPL 和 HTTP API 共用同一层服务函数：

```text
REPL / HTTP API -> app.services -> app.ai_client -> 模型网关
```

当前 agent 模式是一个轻量多轮写作助手。它可以使用选中文本、可选上下文和后端维护的对话历史，并返回用户可读回复以及结构化修改动作。

session API 会把对话历史保存在本地 SQLite 数据库 `data/word_ai.sqlite3` 中；该目录已被 `.gitignore` 忽略。

`actions` 现在使用 v2 动作结构。每个 action 包含：

- `id`：用于预览和后续应用的稳定编号
- `type`：建议操作，例如 `replace_selection`、`replace_range`、`add_comment`、`ask_user`
- `target`：动作要作用的位置
- `preview`：应用前后的文本预览
- `risk_level`：风险等级，可能是 `info`、`low`、`medium`、`high`
- `requires_confirmation`：前端或插件在应用前是否必须让用户确认

客户端应把 actions 当作“建议动作”，而不是直接执行的命令。会修改文档内容的 action 应先展示预览并等待用户确认。

通过 HTTP CLI 进行最小 session 调用：

```text
word-ai-http> agent
Session title [cli]: demo
agent> /text
Enter selected text. Finish with a line containing only EOF.
This method is good and useful.
EOF
Before context (optional):
After context (optional):
Instruction (optional):
agent> 解释这句话的问题，并给一个更正式的版本。
```

## 安全提醒

不要提交 `.env` 或任何真实 API key。真实密钥只应保存在本地。
