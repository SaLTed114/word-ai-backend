Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$AddinRoot = Join-Path $ProjectRoot "word-addin"
$ManifestPath = Join-Path $AddinRoot "manifest.xml"
$TaskpaneUrl = "http://localhost:3000/taskpane.html"
$SettingsUrl = "https://localhost:3443/settings.html"
$ApiUrl = "http://127.0.0.1:8000"
$CondaEnv = "wordplugin"
$CertDir = Join-Path $ProjectRoot ".certs"
$CertPath = Join-Path $CertDir "localhost.pem"
$KeyPath = Join-Path $CertDir "localhost-key.pem"
$OpenSslConfigPath = Join-Path $CertDir "localhost-openssl.cnf"

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

if (-not (Test-Path -LiteralPath $CertDir)) {
    New-Item -ItemType Directory -Path $CertDir | Out-Null
}

if (-not (Test-Path -LiteralPath $CertPath) -or -not (Test-Path -LiteralPath $KeyPath)) {
    Write-Host "Generating local HTTPS certificate for Settings dialog ..."
    @"
[req]
distinguished_name=req_distinguished_name
x509_extensions=v3_req
prompt=no

[req_distinguished_name]
CN=localhost

[v3_req]
subjectAltName=@alt_names

[alt_names]
DNS.1=localhost
IP.1=127.0.0.1
"@ | Set-Content -LiteralPath $OpenSslConfigPath -Encoding ASCII

    openssl req -x509 -newkey rsa:2048 -sha256 -days 365 -nodes `
        -keyout $KeyPath `
        -out $CertPath `
        -config $OpenSslConfigPath | Out-Null
}

$EscapedProjectRoot = $ProjectRoot.Path.Replace("'", "''")
$EscapedAddinRoot = $AddinRoot.Replace("'", "''")
$EscapedCertPath = $CertPath.Replace("'", "''")
$EscapedKeyPath = $KeyPath.Replace("'", "''")
$ApiCommand = "Set-Location -LiteralPath '$EscapedProjectRoot'; $PythonPrefix -m uvicorn app.main:app --reload"
$AddinCommand = "Set-Location -LiteralPath '$EscapedAddinRoot'; python -m http.server 3000"
$SettingsCommand = "Set-Location -LiteralPath '$EscapedProjectRoot'; python scripts\https_static_server.py --directory '$EscapedAddinRoot' --port 3443 --cert '$EscapedCertPath' --key '$EscapedKeyPath'"

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

Write-Host "Starting HTTPS settings server at $SettingsUrl ..."
Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    $SettingsCommand
)

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Manifest:"
Write-Host "  $ManifestPath"
Write-Host ""
Write-Host "Task pane URL:"
Write-Host "  $TaskpaneUrl"
Write-Host ""
Write-Host "Settings URL:"
Write-Host "  $SettingsUrl"
Write-Host ""
Write-Host "If Word blocks the Settings dialog certificate, trust this cert for the current user:"
Write-Host "  $CertPath"
Write-Host ""
Write-Host "In Word, sideload the manifest above, then open the Word AI Assistant task pane."
