#requires -Version 5.1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        throw 'Python 3.11 launcher not found. Install Python 3.11, then run again.'
    }
    & py -3.11 -c 'import sys; print(sys.version)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 is not installed.' }
    if (-not (Test-Path '.venv/Scripts/python.exe')) {
        & py -3.11 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
    }
    $python = Join-Path $root '.venv/Scripts/python.exe'
    & $python -m pip install -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw 'Development dependency installation failed.' }
    & $python -m pre_commit install
    if ($LASTEXITCODE -ne 0) { throw 'Git hook installation failed.' }
    & $python -m pre_commit run --all-files
    if ($LASTEXITCODE -ne 0) {
        throw 'Checks reported changes or errors. Review changes, stage them, and rerun the checks.'
    }
    & $python -m pytest
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
    Write-Host 'Local development checks are ready.'
} finally {
    Pop-Location
}
