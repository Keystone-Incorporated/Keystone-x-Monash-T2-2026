@echo off
setlocal

cd /d "%~dp0"
set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Creating the virtual environment...
    python -m venv "%~dp0.venv"
    if errorlevel 1 goto :error
)

"%PYTHON%" -c "import dash, pandas, openpyxl" >nul 2>&1
if errorlevel 1 (
    echo Installing project dependencies...
    "%PYTHON%" -m pip install -r "%~dp0requirements.txt"
    if errorlevel 1 goto :error
)

echo Starting the Dash dashboard...
start "" /b "%PYTHON%" "%~dp0app.py"

timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:8050/"

echo The dashboard should now be available at http://127.0.0.1:8050/
echo Keep this command window open while using the dashboard.
pause
exit /b 0

:error
echo.
echo The dashboard could not be started. Check the error above.
pause
exit /b 1
