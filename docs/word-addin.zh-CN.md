# Word 插件接入说明

这个目录提供一个最小 Word Web Add-in。它不改后端代码，只把 Word 插件作为前端，调用现有 FastAPI 接口。

## 启动

先确认 `.env` 已经填好，然后运行：

```powershell
.\scripts\start_word_addin.ps1
```

这个脚本会启动两个本地服务：

```text
http://127.0.0.1:8000      后端 API
https://localhost:3443     Word 插件静态文件
```

## 侧载到 Word

在 Word 里侧载这个 manifest：

```text
word-addin/manifest.xml
```

如果已经侧载过旧版本，建议先在 Word 的“我的加载项”里移除旧的 `Word AI Assistant`，关闭 Word 后再重新打开。新的 manifest 会在 Word 顶部增加一个 `Word AI` 选项卡。

## 使用方式

顶部 `Word AI` 选项卡里有：

- `Syntax`
- `Word Choice`
- `Rewrite`
- `Agent`
- `Settings`

前三个按钮会自动读取当前 Word 选区，调用后端，然后直接替换当前选区。如果没有选区，会使用整篇正文。

`Agent` 会打开右侧任务窗格。任务窗格现在只保留对话窗口；Ribbon 命令的结果也会追加到这个窗口里。发送 Agent 消息时会自动读取当前选区，不需要手动刷新。如果 Agent 返回了可替换文本，也会直接替换当前选区。

`Settings` 会打开一个独立设置窗口，里面有后端 API 输入框和 `Check` 按钮；不会占用右侧 Agent 任务窗格。

Word 插件页面必须使用 HTTPS。启动脚本会自动生成本地证书：

```text
.certs/localhost.pem
```

如果 Word 仍然阻止 Settings 窗口，运行：

```powershell
.\scripts\trust_word_addin_cert.ps1
```

然后重启 Word。

如果使用 `dist\WordAI-Setup.exe` 安装包，安装器会在管理员权限下自动完成这一步：它会把安装包内置的 `localhost.pem` 导入 Windows 受信任的根证书颁发机构，并注册本地共享加载项目录。安装完成后如果 Word 已经打开，重启 Word 再添加或打开加载项。

## 注意

- 当前版本仍然是本机开发插件，后端需要保持运行。
- `manifest.xml` 里的任务窗格地址和 Settings 弹窗地址都使用 `https://localhost:3443`。
- 如果 Word 缓存了旧 UI，重启 Word，或移除后重新添加加载项。
- 如果你的 Word 环境要求 HTTPS，需要把静态服务换成 HTTPS，再同步修改 `manifest.xml` 的 `SourceLocation` 和相关 URL。
