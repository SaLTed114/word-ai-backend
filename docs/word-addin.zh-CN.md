# Word 插件接入说明

这个目录提供一个最小 Word Web Add-in。它不改后端代码，只把 Word 任务窗格作为前端，调用现有 FastAPI 接口：

- `GET /health`
- `POST /tasks/syntax`
- `POST /tasks/word-choice`
- `POST /tasks/style`
- `POST /agent/chat`

## 启动

先确认 `.env` 已经填好，然后运行：

```powershell
.\scripts\start_word_addin.ps1
```

这个脚本会启动两个本地服务：

```text
http://127.0.0.1:8000      后端 API
http://localhost:3000      Word 插件任务窗格静态文件
```

## 加到 Word

在 Word 里侧载这个 manifest：

```text
word-addin/manifest.xml
```

侧载后打开 `Word AI Assistant` 任务窗格。

## 使用方式

1. 在 Word 文档里选中一段文字。
2. 在任务窗格点击 `Refresh`，确认当前选区。
3. 点击 `Syntax`、`Word Choice`、`Rewrite` 或使用 `Agent`。
4. 如果结果满意，点击 `Apply to Word` 写回文档。

如果没有选中文本，插件会把整篇正文发给后端；应用结果时也会替换整篇正文。

## 说明

- 当前版本是开发/原型插件，后端仍然运行在本机。
- `manifest.xml` 里的任务窗格地址是 `http://localhost:3000/taskpane.html`。
- 如果你的 Word 环境要求 HTTPS，需要把静态服务换成 HTTPS，再同步修改 `manifest.xml` 的 `SourceLocation`。
