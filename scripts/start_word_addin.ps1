Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$AddinRoot = Join-Path $ProjectRoot "word-addin"
$ManifestPath = Join-Path $AddinRoot "manifest.xml"
$TaskpaneUrl = "http://localhost:3000/taskpane.html"
$ApiUrl = "http://127.0.0.1:8000"
$CondaEnv = "wordplugin"

Set-Location -LiteralPath $ProjectRoot

Write-Host "Word AI Add-in launcher"
Write-Host "Project: $ProjectRoot"

$PreviousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
python -c "import fastapi, uvicorn, openai, pydantic, httpx" 2>$null
$CurrentPythonHasDeps = $LASTEXITCODE -eq 0
$Error.Clear()
conda run -n $CondaEnv python -c "import fastapi, uvicorn, openai, pydantic, httpx" 2>$null
$CondaPythonHasDeps = $LASTEXITCODE -eq 0
$Error.Clear()
$ErrorActionPreference = $PreviousErrorActionPreference

if ($CurrentPythonHasDeps) {
    $PythonPrefix = "python"
} elseif ($CondaPythonHasDeps) {
    $PythonPrefix = "conda run -n $CondaEnv python"
} else {
    Write-Host ""
    Write-Host "Missing Python dependencies. Run this first:" -ForegroundColor Yellow
    Write-Host "  conda activate $CondaEnv"
    Write-Host "  pip install -r requirements.txt"
    exit 1
}

if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot ".env"))) {
    Write-Host ""
    Write-Host "Warning: .env was not found. Copy .env.example to .env and fill in your API settings." -ForegroundColor Yellow
}

$EscapedProjectRoot = $ProjectRoot.Path.Replace("'", "''")
$EscapedAddinRoot = $AddinRoot.Replace("'", "''")
$ApiCommand = "Set-Location -LiteralPath '$EscapedProjectRoot'; $PythonPrefix -m uvicorn app.main:app --reload"
$AddinCommand = "Set-Location -LiteralPath '$EscapedAddinRoot'; python -m http.server 3000"

Write-Host "Starting API server at $ApiUrl ..."
Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    $ApiCommand
)

Write-Host "Starting add-in static server at $TaskpaneUrl ..."
Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    $AddinCommand
)

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Manifest:"
Write-Host "  $ManifestPath"
Write-Host ""
Write-Host "Task pane URL:"
Write-Host "  $TaskpaneUrl"
Write-Host ""
Write-Host "In Word, sideload the manifest above, then open the Word AI Assistant task pane."
