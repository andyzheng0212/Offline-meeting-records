@echo off
setlocal
cd /d %~dp0

if not exist .venv (
  echo [INFO] Creating virtual environment...
  py -3.10 -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create venv. Ensure Python 3.10+ is installed and on PATH.
    pause
    exit /b 1
  )
  call .venv\Scripts\activate
  python -m pip install --upgrade pip
  if exist requirements.txt pip install -r requirements.txt
  if exist requirements-web.txt pip install -r requirements-web.txt
) else (
  call .venv\Scripts\activate
)

echo [INFO] Starting local web UI (offline)...
streamlit run app_web.py

echo.
echo [INFO] If the browser didn't open, visit http://localhost:8501
pause
