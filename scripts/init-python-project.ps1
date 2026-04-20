param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectPath,

    [string]$PythonVersion = "3.13"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ProjectPath)) {
    New-Item -Path $ProjectPath -ItemType Directory -Force | Out-Null
}

Set-Location -LiteralPath $ProjectPath

if (-not (Test-Path -LiteralPath ".venv")) {
    py -$PythonVersion -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install -U pip

if (-not (Test-Path -LiteralPath "requirements.txt")) {
    @"
# Add your direct dependencies here.
# Example:
# Flask==3.0.3
"@ | Set-Content -LiteralPath "requirements.txt" -Encoding UTF8
}

if (-not (Test-Path -LiteralPath ".gitignore")) {
    @"
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ipynb_checkpoints/
"@ | Set-Content -LiteralPath ".gitignore" -Encoding UTF8
}

Write-Host ""
Write-Host "Project initialized: $ProjectPath"
Write-Host "Next steps:"
Write-Host "1) .\.venv\Scripts\Activate.ps1"
Write-Host "2) pip install -r requirements.txt"
Write-Host "3) pip freeze > requirements.lock.txt"
