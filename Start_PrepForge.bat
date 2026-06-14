@echo off
title PrepForge - Launcher
setlocal enabledelayedexpansion

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "VENV_PY=%BACKEND%\.venv\Scripts\python.exe"
REM Uncommon ports so PrepForge does not clash with other apps on 3000/8000.
set "BACKEND_PORT=8077"
set "FRONTEND_PORT=3077"
set "BACKEND_URL=http://localhost:%BACKEND_PORT%"
set "FRONTEND_URL=http://localhost:%FRONTEND_PORT%"

echo ==================================================
echo    PrepForge - AI Interview Preparation Platform
echo    One-click launcher - no Docker required
echo ==================================================
echo.

REM --- 1) Python virtual environment -------------------------------------
if exist "%VENV_PY%" goto venv_ok
echo [INFO] Creating Python virtual environment, first run only...
where py >nul 2>nul
if not errorlevel 1 (
    py -m venv "%BACKEND%\.venv"
) else (
    python -m venv "%BACKEND%\.venv"
)
if not exist "%VENV_PY%" (
    echo [ERROR] Could not create the Python virtual environment.
    echo         Install Python 3.12+ from https://www.python.org/downloads/
    echo         Make sure py or python is on your PATH, then run this again.
    echo.
    pause
    exit /b 1
)
echo [INFO] Installing backend dependencies, this can take a minute...
"%VENV_PY%" -m pip install --upgrade pip
pushd "%BACKEND%"
"%VENV_PY%" -m pip install -e ".[dev]"
popd
:venv_ok
echo [INFO] Backend environment ready.

REM --- 2) Node.js / frontend dependencies --------------------------------
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install Node 18+ from https://nodejs.org/ then retry.
    echo.
    pause
    exit /b 1
)
if exist "%FRONTEND%\node_modules" goto node_ok
echo [INFO] Installing frontend dependencies, first run only, about 1-2 minutes...
pushd "%FRONTEND%"
call npm install --no-audit --no-fund
popd
:node_ok
echo [INFO] Frontend dependencies ready.

REM --- 3) Local config: SQLite, no external database needed --------------
if exist "%BACKEND%\.env" goto env_ok
echo [INFO] Creating local backend\.env using SQLite...
(
    echo APP_NAME=PrepForge
    echo ENVIRONMENT=development
    echo DEBUG=true
    echo API_V1_PREFIX=/api/v1
    echo BACKEND_CORS_ORIGINS=["http://localhost:3077"]
    echo SECRET_KEY=prepforge-local-dev-secret-change-me-0123456789abcdef
    echo ACCESS_TOKEN_EXPIRE_MINUTES=30
    echo REFRESH_TOKEN_EXPIRE_DAYS=14
    echo DATABASE_URL=sqlite+aiosqlite:///./prepforge_dev.db
    echo READ_DATABASE_URL=
    echo RATE_LIMIT_ENABLED=false
    echo CACHE_ENABLED=false
    echo ALLOW_LOCAL_CODE_EXECUTION=true
    echo METRICS_ENABLED=true
    echo LLM_PROVIDER=ollama
) > "%BACKEND%\.env"
:env_ok

REM --- 4) Start the backend: migrate then uvicorn -----------------------
echo [INFO] Starting backend on %BACKEND_URL% ...
start "PrepForge Backend" /d "%BACKEND%" cmd /k ".venv\Scripts\python.exe -m alembic upgrade head && .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT%"

echo [INFO] Waiting for the backend to be ready...
set /a TRIES=0
:wait_api
timeout /t 3 /nobreak >nul
curl -s %BACKEND_URL%/health 2>nul | findstr "ok" >nul
if not errorlevel 1 goto api_ready
set /a TRIES+=1
if !TRIES! lss 20 goto wait_api
echo [WARN] Backend not responding yet. Check the PrepForge Backend window for errors.
:api_ready

REM --- 5) Start the frontend: Next.js dev server on a fixed port ---------
REM The child process inherits this variable; Next uses it to proxy /api.
set "NEXT_PUBLIC_API_BASE_URL=%BACKEND_URL%"
echo [INFO] Starting frontend on %FRONTEND_URL% ...
start "PrepForge Frontend" /d "%FRONTEND%" cmd /k "npm run dev -- -p %FRONTEND_PORT%"

echo [INFO] Waiting for the frontend to compile, please wait...
timeout /t 12 /nobreak >nul
start "" "%FRONTEND_URL%"

echo.
echo ==================================================
echo    PREPFORGE IS RUNNING
echo ==================================================
echo    Web app   : %FRONTEND_URL%
echo    API       : %BACKEND_URL%
echo    API docs  : %BACKEND_URL%/docs
echo    Health    : %BACKEND_URL%/health
echo ==================================================
echo.
echo If the browser shows 404, wait a few seconds for the frontend to finish
echo compiling, then refresh %FRONTEND_URL% .
echo.
echo Keep the PrepForge Backend and PrepForge Frontend windows open.
echo To stop everything, run Stop_PrepForge.bat or close both windows.
echo.
echo Tip: install Ollama from https://ollama.com and run "ollama serve" for
echo      richer AI. Without it the app still works with built-in fallbacks.
echo.
echo Press any key to close THIS launcher window. The app keeps running.
pause >nul
endlocal
