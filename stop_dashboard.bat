@echo off
setlocal

echo Looking for the Dash process on port 8050...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8050" ^| findstr "LISTENING"') do (
    echo Stopping process %%P...
    taskkill /PID %%P /F >nul 2>&1
)

echo Dashboard stop command completed.
pause
exit /b 0
