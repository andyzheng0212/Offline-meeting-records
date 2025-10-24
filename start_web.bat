@echo off
setlocal
cd /d %~dp0

set "PYTHON_CMD="
set "PYTHON_ARGS="

where py >nul 2>nul
if %errorlevel%==0 (
  py -3.14 -c "exit()" >nul 2>&1
  if %errorlevel%==0 (
    set "PYTHON_CMD=py"
    set "PYTHON_ARGS=-3.14"
  ) else (
    py -3 -c "exit()" >nul 2>&1
    if %errorlevel%==0 (
      set "PYTHON_CMD=py"
      set "PYTHON_ARGS=-3"
    ) else (
      set "PYTHON_CMD=py"
      set "PYTHON_ARGS="
    )
  )
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set "PYTHON_CMD=python"
    set "PYTHON_ARGS="
  )
)

if not defined PYTHON_CMD (
  echo [ERROR] Python 3.x is required. Please install Python 3.10-3.14 and ensure it is on PATH.
  pause
  exit /b 1
)

set "ACTIVATE=.venv\\Scripts\\activate"

if not exist .venv (
  echo [INFO] Creating virtual environment...
  call %PYTHON_CMD% %PYTHON_ARGS% -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create venv. Please confirm Python is installed and accessible.
    pause
    exit /b 1
  )
  call "%ACTIVATE%"
  python -m pip install --upgrade pip
  if exist requirements.txt python -m pip install -r requirements.txt
  if exist requirements-web.txt python -m pip install -r requirements-web.txt
) else (
  call "%ACTIVATE%"
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
