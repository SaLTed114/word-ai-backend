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
- FastAPI HTTP endpoints for backend tasks
- External prompt templates
- ShanghaiTech GenAI gateway direct endpoint support

## Quick Start

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Create `.env` from `.env.example` and fill in your own API configuration:

```env
OPENAI_API_KEY=
OPENAI_MODEL=GPT-5.4
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_ENDPOINT=https://genaiapi.shanghaitech.edu.cn/api/v1/start
OPENAI_PROXY_URL=
OPENAI_TRUST_ENV=false
OPENAI_USE_JSON_MODE=true
```

3. Run the REPL:

```powershell
python -m app.repl
```

4. Or run the HTTP API:

```powershell
uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

5. Try a REPL command:

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

## HTTP API

- `GET /health`: Check service and AI configuration status
- `POST /tasks/syntax`: Check grammar, spelling, punctuation, and clarity
- `POST /tasks/word-choice`: Check word choice and phrasing
- `POST /tasks/style`: Rewrite text into a target style
- `POST /agent/chat`: Chat with the writing assistant using optional selected text and history

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

The agent mode is currently a lightweight multi-turn writing assistant. It can use selected text, optional context, and conversation history, then return both a user-facing reply and structured edit actions.

## Security

Do not commit `.env` or API keys. Keep real credentials local.
