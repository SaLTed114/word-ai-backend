Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$CertPath = Join-Path $ProjectRoot ".certs\localhost.pem"

if (-not (Test-Path -LiteralPath $CertPath)) {
    Write-Host "Certificate was not found:" -ForegroundColor Yellow
    Write-Host "  $CertPath"
    Write-Host ""
    Write-Host "Run this first:"
    Write-Host "  .\scripts\start_word_addin.ps1"
    exit 1
}

Write-Host "Adding local Word add-in HTTPS certificate to CurrentUser Root store..."
certutil -user -addstore Root $CertPath
Write-Host "Done. Restart Word after trusting the certificate."
