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
- FastAPI HTTP 接口
- 外置 prompt 模板
- 支持上海科技大学 GenAI 网关 direct endpoint 调用方式

## 快速开始

1. 安装依赖：

```powershell
pip install -r requirements.txt
```

2. 复制 `.env.example` 为 `.env`，并填写你自己的 API 配置：

```env
OPENAI_API_KEY=
OPENAI_MODEL=GPT-5.4
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_ENDPOINT=https://genaiapi.shanghaitech.edu.cn/api/v1/start
OPENAI_PROXY_URL=
OPENAI_TRUST_ENV=false
OPENAI_USE_JSON_MODE=true
```

3. 启动 REPL：

```powershell
python -m app.repl
```

4. 或者启动 HTTP API：

```powershell
uvicorn app.main:app --reload
```

然后打开：

```text
http://127.0.0.1:8000/docs
```

5. 试用一个 REPL 命令：

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

## HTTP API

- `GET /health`：检查服务状态和 AI 配置状态
- `POST /tasks/syntax`：检查语法、拼写、标点和表达清晰度
- `POST /tasks/word-choice`：检查用词和短语表达
- `POST /tasks/style`：将文本改写为目标文风
- `POST /agent/chat`：基于可选选中文本和历史记录进行写作助手对话

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

当前 agent 模式是一个轻量多轮写作助手。它可以使用选中文本、可选上下文和对话历史，并返回用户可读回复以及结构化修改动作。

## 安全提醒

不要提交 `.env` 或任何真实 API key。真实密钥只应保存在本地。
