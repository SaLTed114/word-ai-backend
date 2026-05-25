# Word AI Backend

A clean backend prototype for a Word/WPS AI writing assistant.

This repository currently focuses on backend capability validation through a FastAPI HTTP API and a small HTTP CLI before rebuilding the UI or Office/WPS integration.

## Documentation

- [中文快速开始](docs/README.zh-CN.md)
- [详细仓库介绍](docs/repository-overview.zh-CN.md)

## Current Features

- Syntax checking
- Word choice checking
- Style rewriting
- Agent-style iterative writing assistance
- Backend-managed agent sessions stored in local SQLite
- Session memory for document summary, writing goals, key terms, and user preferences
- Backend context builder for document text, selections, and scope-aware context windows
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

4. Run the HTTP API:

```powershell
uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

5. Run the HTTP CLI in another terminal:

```powershell
python -m app.api_cli
```

The HTTP CLI sends real requests to the running backend and prints `reply`, `final_text`, and `actions` without requiring handwritten PowerShell JSON.

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
- `context`: Preview `POST /context/build`
- `agent`: Create an agent session and chat through `POST /agent/sessions/{session_id}/messages`
- `sessions`: List recent agent sessions
- `messages <id>`: Show messages in one session
- `memory <id>`: Show memory for one session
- `set-memory <id>`: Replace memory for one session

Inside `agent` mode:

- `/context`: Attach document text, selected text, and scope for later turns
- `/clear-context`: Clear the attached document context
- `/memory`: Show session memory
- `/set-memory`: Replace session memory
- `/messages`: Show messages in the current session
- `/new`: Start a new session
- `/exit`: Leave agent mode

You can also point the CLI at another backend URL:

```powershell
python -m app.api_cli --base-url http://127.0.0.1:8000
```

## Agent Flow Test

Start the backend first:

```powershell
uvicorn app.main:app --reload
```

Then run the fixed agent flow test:

```powershell
python .\scripts\test_agent_flow.py
```

If you want to test the backend flow without a real model call, run:

```powershell
python .\scripts\test_agent_flow.py --mock
```

The script tests:

- `GET /health`
- `POST /context/build`
- `POST /agent/sessions`
- `PUT /agent/sessions/{session_id}/memory`
- `POST /agent/sessions/{session_id}/messages`
- `GET /agent/sessions/{session_id}/messages`
- `DELETE /agent/sessions/{session_id}`

It uses a fixed methods-section paragraph, sets session memory, sends a Chinese agent instruction, and checks that the agent response contains structured output.

## Agent Scenario Test

Run the default multi-turn scenario:

```powershell
python .\scripts\agent_scenario_test.py
```

Run it without a real model call:

```powershell
python .\scripts\agent_scenario_test.py --mock
```

The default scenario lives at:

```text
tests/scenarios/academic_rewrite.zh-CN.json
```

Scenario files define session memory, document context, multiple user turns, and lightweight expectations such as required actions, final text, message count, and action schema.

## Web Agent Demo

Start the backend first:

```powershell
uvicorn app.main:app --reload
```

Then open:

```text
examples/simple-web/index.html
```

The demo has a document editor on the left and an agent chat panel on the right. It calls the session-based agent API, sends `document_context`, and lets you save session memory before chatting.

## HTTP API

- `GET /health`: Check service and AI configuration status
- `POST /tasks/syntax`: Check grammar, spelling, punctuation, and clarity
- `POST /tasks/word-choice`: Check word choice and phrasing
- `POST /tasks/style`: Rewrite text into a target style
- `POST /context/build`: Convert document text plus selection data into a model-ready `TextRequest`
- `POST /agent/sessions`: Create a backend-managed agent session
- `GET /agent/sessions`: List recent agent sessions
- `GET /agent/sessions/{session_id}`: Get one agent session
- `DELETE /agent/sessions/{session_id}`: Delete one agent session
- `GET /agent/sessions/{session_id}/messages`: List messages in a session
- `GET /agent/sessions/{session_id}/memory`: Get session memory
- `PUT /agent/sessions/{session_id}/memory`: Replace session memory
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

The HTTP API calls the shared service layer:

```text
HTTP API -> app.services -> app.ai_client -> model gateway
```

The agent mode is currently a lightweight multi-turn writing assistant. It can use selected text, optional context, and backend-managed conversation history, then return both a user-facing reply and structured edit actions.

Agent sessions store conversation history in a local SQLite database at `data/word_ai.sqlite3`, which is ignored by git.

Session memory is also stored in SQLite. Each session can keep:

- `document_summary`
- `writing_goals`
- `key_terms`
- `user_preferences`

Agent turns automatically include this memory in the prompt. Memory is explicit in v1: clients or the CLI update it through `PUT /agent/sessions/{session_id}/memory`; the model does not rewrite memory by itself yet.

The context builder accepts document-level input:

- `document_text`: available plain text from the document
- `selection.text` or `selection.start` / `selection.end`: the active user selection
- `active_scope`: `selection`, `paragraph`, `section`, or `document`
- `context_window_chars`: how much surrounding text to keep

It returns a normalized `TextRequest` with selected text plus before/after context. `before` and `after` are kept as the internal model-ready context format; new clients should usually send `document_context` and let the backend fill those fields.

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
agent> Explain this sentence and suggest a formal rewrite.
```

## Security

Do not commit `.env` or API keys. Keep real credentials local.
