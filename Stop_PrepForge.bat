@echo off
title PrepForge - Stop
echo Stopping PrepForge backend and frontend windows...

REM Close the named launcher windows; /T also stops child processes
REM (uvicorn / node) started inside them.
taskkill /FI "WINDOWTITLE eq PrepForge Backend*" /T /F >nul 2>nul
taskkill /FI "WINDOWTITLE eq PrepForge Frontend*" /T /F >nul 2>nul

REM Free the ports in case anything is still bound to them.
for %%P in (8077 3077) do (
    for /f "tokens=5" %%K in ('netstat -ano ^| findstr ":%%P" ^| findstr "LISTENING"') do (
        taskkill /PID %%K /F >nul 2>nul
    )
)

echo Done. PrepForge has been stopped.
timeout /t 2 /nobreak >nul
