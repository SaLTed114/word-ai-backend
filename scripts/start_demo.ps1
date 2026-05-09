Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DemoPath = Join-Path $ProjectRoot "examples\simple-web\index.html"
$DocsUrl = "http://127.0.0.1:8000/docs"
$ApiUrl = "http://127.0.0.1:8000"

Set-Location -LiteralPath $ProjectRoot

Write-Host "Word AI Backend demo launcher"
Write-Host "Project: $ProjectRoot"

python -c "import fastapi, uvicorn, openai, pydantic, httpx" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Missing Python dependencies. Run this first:" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt"
    exit 1
}

if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot ".env"))) {
    Write-Host ""
    Write-Host "Warning: .env was not found. Copy .env.example to .env and fill in your API settings." -ForegroundColor Yellow
}

$EscapedProjectRoot = $ProjectRoot.Path.Replace("'", "''")
$ServerCommand = "Set-Location -LiteralPath '$EscapedProjectRoot'; python -m uvicorn app.main:app --reload"

Write-Host "Starting API server at $ApiUrl ..."
Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    $ServerCommand
)

Start-Sleep -Seconds 2

Write-Host "Opening API docs: $DocsUrl"
Start-Process $DocsUrl

Write-Host "Opening static editor demo: $DemoPath"
Start-Process $DemoPath

Write-Host ""
Write-Host "If the pages open before the server is ready, refresh the browser after a few seconds."
