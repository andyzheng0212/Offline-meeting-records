$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (!(Test-Path ".\.venv")) {
  Write-Host "[INFO] Creating virtual environment..."
  py -3.10 -m venv .venv
  & .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  if (Test-Path ".\requirements.txt") { pip install -r requirements.txt }
  if (Test-Path ".\requirements-web.txt") { pip install -r requirements-web.txt }
} else {
  & .\.venv\Scripts\Activate.ps1
}

Write-Host "[INFO] Starting local web UI (offline)..."
streamlit run app_web.py

Write-Host "`n[INFO] If the browser didn't open, visit http://localhost:8501"
Read-Host "Press Enter to exit"
