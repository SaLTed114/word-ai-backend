# Word AI Backend

A clean backend prototype for a Word/WPS AI writing assistant.

This repository currently focuses on backend capability validation through a REPL and a small HTTP API before rebuilding the UI or Office/WPS integration.

## Documentation

- [中文快速开始](docs/README.zh-CN.md)
- [详细仓库介绍](docs/repository-overview.zh-CN.md)

## Current Features

- Syntax checking
- Word choice checking
- Style rewriting
- Agent-style iterative writing assistance
- Backend-managed agent sessions stored in local SQLite
- FastAPI HTTP endpoints for backend tasks
- External prompt templates
- ShanghaiTech GenAI gateway direct endpoint support

## Quick Start

1. Create and activate the recommended conda environment:

```powershell
conda create -n wordplugin python=3.11
conda activate wordplugin
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Create `.env` from `.env.example` and fill in your own API configuration:

```env
OPENAI_API_KEY=
OPENAI_MODEL=GPT-5.4
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_ENDPOINT=https://genaiapi.shanghaitech.edu.cn/api/v1/start
OPENAI_PROXY_URL=
OPENAI_TRUST_ENV=false
OPENAI_USE_JSON_MODE=true
```

4. Run the REPL:

```powershell
python -m app.repl
```

5. Or run the HTTP API:

```powershell
uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

6. Or run the HTTP CLI after starting the API:

```powershell
python -m app.api_cli
```

The HTTP CLI sends real requests to the running backend and prints `reply`, `final_text`, and `actions` without requiring handwritten PowerShell JSON.

7. Try a REPL command:

```text
word-ai> syntax
Enter selected text. Finish with a line containing only EOF.
He dont know what to did yesterday.
EOF
```

## REPL Commands

- `config`: Show or update model configuration
- `syntax`: Check grammar, spelling, punctuation, and clarity
- `word`: Check word choice and phrasing
- `style`: Rewrite text into a target style
- `agent`: Start an iterative writing-assistant chat
- `help`: Show available commands
- `exit`: Quit

## HTTP CLI

Start the backend first:

```powershell
uvicorn app.main:app --reload
```

Then run:

```powershell
python -m app.api_cli
```

Available commands:

- `health`: Check backend health
- `syntax`: Call `POST /tasks/syntax`
- `word`: Call `POST /tasks/word-choice`
- `style`: Call `POST /tasks/style`
- `agent`: Create an agent session and chat through `POST /agent/sessions/{session_id}/messages`
- `sessions`: List recent agent sessions
- `messages <id>`: Show messages in one session

Inside `agent` mode:

- `/text`: Attach selected text for later turns
- `/clear-text`: Clear the attached selected text
- `/messages`: Show messages in the current session
- `/new`: Start a new session
- `/exit`: Leave agent mode

You can also point the CLI at another backend URL:

```powershell
python -m app.api_cli --base-url http://127.0.0.1:8000
```

## HTTP API

- `GET /health`: Check service and AI configuration status
- `POST /tasks/syntax`: Check grammar, spelling, punctuation, and clarity
- `POST /tasks/word-choice`: Check word choice and phrasing
- `POST /tasks/style`: Rewrite text into a target style
- `POST /agent/sessions`: Create a backend-managed agent session
- `GET /agent/sessions`: List recent agent sessions
- `GET /agent/sessions/{session_id}`: Get one agent session
- `DELETE /agent/sessions/{session_id}`: Delete one agent session
- `GET /agent/sessions/{session_id}/messages`: List messages in a session
- `POST /agent/sessions/{session_id}/messages`: Send one user message and receive one assistant turn

Example request for `POST /tasks/syntax`:

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

## Architecture

Both the REPL and HTTP API call the same service layer:

```text
REPL / HTTP API -> app.services -> app.ai_client -> model gateway
```

The agent mode is currently a lightweight multi-turn writing assistant. It can use selected text, optional context, and backend-managed conversation history, then return both a user-facing reply and structured edit actions.

Agent sessions store conversation history in a local SQLite database at `data/word_ai.sqlite3`, which is ignored by git.

`actions` use the v2 action schema. Each action includes:

- `id`: stable id for preview and later application
- `type`: suggested operation, such as `replace_selection`, `replace_range`, `add_comment`, or `ask_user`
- `target`: where the action applies
- `preview`: before/after text for user review
- `risk_level`: `info`, `low`, `medium`, or `high`
- `requires_confirmation`: whether the UI must ask before applying the action

Clients should treat actions as proposals. Editing actions should be previewed and confirmed before changing a document.

Minimal session flow through the HTTP CLI:

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
agent> Explain this sentence and suggest a formal rewrite.
```

## Security

Do not commit `.env` or API keys. Keep real credentials local.
