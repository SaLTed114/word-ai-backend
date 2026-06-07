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
- Formula / equation handling (LaTeX, OMML)
- Agent-style iterative writing assistance
- Subagent dispatch for focused editing tasks (proofread, academic polish, summarize, translate, formula, and custom)
- Auto-planning subagents via LLM planner
- LLM-based merge of multiple subagent results
- Backend-managed agent sessions stored in local SQLite
- Session memory for document summary, writing goals, key terms, and user preferences
- Backend context builder for document text, selections, and scope-aware context windows
- FastAPI HTTP endpoints for backend tasks
- External prompt templates
- Skill management API (CRUD for markdown skill files)
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
- `skills`: List available skills

Inside `agent` mode:

- `/context`: Attach document text, selected text, and scope for later turns
- `/clear-context`: Clear the attached document context
- `/memory`: Show session memory
- `/set-memory`: Replace session memory
- `/messages`: Show messages in the current session
- `/subagents <name,...>`: Dispatch the current message to one or more subagents (e.g. `/subagents proofread,academic_polish`)
- `/plan`: Ask the LLM planner to suggest subagents for the current task
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
- `GET /settings/ai-config`: Read current AI configuration
- `PUT /settings/ai-config`: Update AI configuration at runtime
- `POST /tasks/syntax`: Check grammar, spelling, punctuation, and clarity
- `POST /tasks/word-choice`: Check word choice and phrasing
- `POST /tasks/style`: Rewrite text into a target style
- `POST /tasks/formula`: Handle LaTeX, equations, and Word equation output
- `POST /context/build`: Convert document text plus selection data into a model-ready `TextRequest`
- `POST /agent/sessions`: Create a backend-managed agent session
- `GET /agent/sessions`: List recent agent sessions
- `GET /agent/sessions/{session_id}`: Get one agent session
- `DELETE /agent/sessions/{session_id}`: Delete one agent session
- `GET /agent/sessions/{session_id}/messages`: List messages in a session
- `GET /agent/sessions/{session_id}/memory`: Get session memory
- `PUT /agent/sessions/{session_id}/memory`: Replace session memory
- `POST /agent/sessions/{session_id}/messages`: Send one user message and receive one assistant turn (supports subagent dispatch via `subagents`, `auto_subagents`, or `planned_subagents` fields)
- `POST /agent/sessions/{session_id}/subagents/plan`: Ask the LLM planner to suggest subagent calls for a task
- `POST /agent/sessions/{session_id}/subagents/run`: Run a single subagent independently (stepwise mode)
- `POST /agent/sessions/{session_id}/subagents/merge`: Merge subagent results and persist messages (stepwise mode)
- `GET /skills`: List available skill files
- `GET /skills/{name}`: Read a skill file content
- `POST /skills`: Create a new skill file
- `PUT /skills/{name}`: Update or rename a skill file
- `DELETE /skills/{name}`: Delete a skill file

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

## Subagents

The agent supports dispatching user requests to specialized subagents that each focus on one editing domain. This gives better results for multi-faceted tasks (e.g. "proofread AND polish this paragraph") than a single monolithic prompt.

### Preset Subagents

| Name | Skill File | Description |
|------|-----------|-------------|
| `proofread` | `skills/proofread.md` | Grammar, spelling, punctuation, clarity |
| `academic_polish` | `skills/academic-polish.md` | Formal academic English polishing |
| `summarize` | `skills/summarize.md` | Concise summarization |
| `translate_zh` | `skills/translate-zh.md` | Chinese-English translation |
| `formula` | `skills/formula.md` | LaTeX, equations, Word equation output |

Each preset subagent has:
- A **skill file** with domain-specific instructions injected into the prompt
- **Allowed action types** restricting what editing actions it can return
- Context mode controlling how much surrounding text is included

Custom subagent names (not in the preset registry) are also supported — they run with a generic writing-assistant prompt and the caller-supplied instruction.

### Dispatch Modes

Three ways to invoke subagents from `POST /agent/sessions/{session_id}/messages`:

1. **Explicit list** (`subagents` field): Provide a list of preset or custom subagent names.
   ```json
   { "message": "Check grammar and improve academic tone.", "subagents": ["proofread", "academic_polish"] }
   ```

2. **Auto-planning** (`auto_subagents: true`): The backend calls an LLM planner that decides which subagents (if any) to dispatch. The planner sees available preset names, skill files, selected text, and the user message. It returns up to 3 subagent calls with custom instructions.
   ```json
   { "message": "Make this clearer and more formal.", "auto_subagents": true }
   ```

3. **Planned subagents** (`planned_subagents` field): The client calls `POST /agent/sessions/{session_id}/subagents/plan` first, reviews the plan, then sends the approved calls.
   ```json
   { "message": "...", "planned_subagents": [{"name": "proofread", "instruction": "Focus on grammar only."}] }
   ```

### Stepwise Mode

For clients that need fine-grained control, the subagent flow can be split into explicit steps:

1. `POST /agent/sessions/{session_id}/subagents/run` — run one subagent, get its `TaskResponse` without persisting messages
2. `POST /agent/sessions/{session_id}/subagents/merge` — merge results from one or more `run` calls, persist user + assistant messages, and optionally run LLM merge

This lets the client inspect or modify individual subagent responses before merging.

### LLM Merge

After subagents run, their `TaskResponse` results are merged by concatenation (replies joined, actions collected, last non-null `final_text` kept). When `llm_merge_subagents` is true (default), the merged result is sent through an additional LLM call that reconciles conflicts and produces a single coherent `TaskResponse`.

### Skill Management

Skills are markdown files under `skills/` that contain domain-specific prompt instructions. The `/skills` CRUD API lets clients list, read, create, update, and delete skill files at runtime. Preset subagents each have a default skill file; custom skills can be passed per-turn via the `skills` field and are injected into the subagent prompt.

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
