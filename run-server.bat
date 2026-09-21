@echo off
title Restaurant Ordering Server
cd /d "%~dp0"
echo.
echo ========================================
echo   RESTAURANT ORDERING SERVER
echo ========================================
echo.
echo Computer: http://127.0.0.1:8010/
echo Phone:    http://192.168.1.122:8010/
echo Cashier:  http://127.0.0.1:8010/login
echo.
echo Keep this window open while using the ordering system.
echo Press Ctrl+C to stop the server.
echo.
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8010/"
"D:\python\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8010
echo.
echo Server stopped.
pause
