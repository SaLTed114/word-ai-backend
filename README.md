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
- Static TXT editor demo that calls the backend API
- External prompt templates
- ShanghaiTech GenAI gateway direct endpoint support

## Quick Start

1. Create and activate the recommended conda environment:

```powershell
conda create -n wordplugin python=3.11
conda activate wordplugin
```

The double-click batch launcher expects this environment name by default. If you use a different name, edit `CONDA_ENV` in `scripts/start_demo.bat`.

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

6. Or open the static text editor demo:

```text
examples/simple-web/index.html
```

The demo needs the HTTP API running at `http://127.0.0.1:8000`.

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

## Static Web Demo

The static demo in `examples/simple-web/` is a small TXT editor. It can:

- Open and save `.txt` content
- Send the full text or current selection to backend tasks
- Run syntax, word choice, style, and agent requests
- Show `reply`, `final_text`, and structured `actions`
- Apply returned text back to the editor

It is intentionally framework-free so the data flow stays easy to inspect before moving to Word/WPS integration.

You can launch the API server, API docs, and static editor demo with:

```powershell
.\scripts\start_demo.ps1
```

On Windows, you can also double-click:

```text
scripts/start_demo.bat
```

The batch wrapper activates the `wordplugin` conda environment before running the PowerShell launcher. Edit `CONDA_ENV` inside the file if your environment has a different name.

Recommended first-time setup for the batch launcher:

```powershell
conda create -n wordplugin python=3.11
conda activate wordplugin
pip install -r requirements.txt
```

If PowerShell blocks the script, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\start_demo.ps1
```

## Security

Do not commit `.env` or API keys. Keep real credentials local.
