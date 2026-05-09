# Word AI Backend

A clean backend prototype for a Word/WPS AI writing assistant.

This repository currently focuses on backend capability validation through a REPL before rebuilding the UI or Office/WPS integration.

## Documentation

- [中文快速开始](docs/README.zh-CN.md)
- [详细仓库介绍](docs/repository-overview.zh-CN.md)

## Current Features

- Syntax checking
- Word choice checking
- Style rewriting
- Agent-style iterative writing assistance
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

4. Try a command:

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

## Security

Do not commit `.env` or API keys. Keep real credentials local.
