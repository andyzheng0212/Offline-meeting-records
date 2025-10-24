$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Resolve-PythonLauncher {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            py -3.14 -c "import sys" *> $null
            return @{ Cmd = "py"; Args = @("-3.14") }
        } catch {
        }
        try {
            py -3 -c "import sys" *> $null
            return @{ Cmd = "py"; Args = @("-3") }
        } catch {
        }
        return @{ Cmd = "py"; Args = @() }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @{ Cmd = "python"; Args = @() }
    }
    return $null
}

$launcher = Resolve-PythonLauncher
if (-not $launcher) {
    Write-Error "Python 3.10-3.14 is required. Please install Python and ensure it is on PATH."
}

$activateScript = ".\.venv\Scripts\Activate.ps1"

if (!(Test-Path ".\.venv")) {
    Write-Host "[INFO] Creating virtual environment..."
    $venvArgs = @($launcher.Args + @("-m", "venv", ".venv"))
    & $launcher.Cmd @venvArgs
    if (!(Test-Path ".\.venv")) {
        Write-Error "Failed to create virtual environment. Please confirm Python is installed."
    }
    & $activateScript
    python -m pip install --upgrade pip
    if (Test-Path ".\requirements.txt") { python -m pip install -r requirements.txt }
    if (Test-Path ".\requirements-web.txt") { python -m pip install -r requirements-web.txt }
} else {
    & $activateScript
}

Write-Host "[INFO] Starting local web UI (offline)..."
streamlit run app_web.py

Write-Host "`n[INFO] If the browser didn't open, visit http://localhost:8501"
Read-Host "Press Enter to exit"
