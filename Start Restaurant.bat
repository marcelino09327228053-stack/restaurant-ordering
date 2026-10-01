@echo off
setlocal
title Restaurant Ordering Server
cd /d "%~dp0"
echo Restaurant Ordering: http://127.0.0.1:8010/
echo Cashier login: http://127.0.0.1:8010/login
echo Keep this window open while using the app.
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Missing Python environment. Please run setup first.
  pause
  exit /b 1
)
start "" /min powershell.exe -NoProfile -WindowStyle Hidden -Command "for ($i=0; $i -lt 30; $i++) { try { $r = Invoke-WebRequest 'http://127.0.0.1:8010/health' -UseBasicParsing; if ($r.StatusCode -eq 200) { Start-Process 'chrome.exe' 'http://127.0.0.1:8010/'; exit } } catch {}; Start-Sleep -Seconds 1 }"
"%~dp0.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8010
echo Server stopped.
pause
