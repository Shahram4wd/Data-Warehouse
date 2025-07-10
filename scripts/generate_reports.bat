@echo off
REM Script to generate automation reports manually on Windows
REM Usage: generate_reports.bat [crm] [time-window]

setlocal enabledelayedexpansion

REM Default values
set CRM=%1
if "%CRM%"=="" set CRM=all

set TIME_WINDOW=%2
if "%TIME_WINDOW%"=="" set TIME_WINDOW=24

echo 🤖 Generating automation reports...
echo CRM: %CRM%
echo Time Window: %TIME_WINDOW% hours
echo.

REM Navigate to project directory
cd /d "%~dp0\.."

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo ✅ Activated virtual environment
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo ✅ Activated virtual environment
)

REM Run the management command
python manage.py generate_automation_reports ^
    --time-window %TIME_WINDOW% ^
    --detailed ^
    --crm %CRM% ^
    --export-json ^
    --output-dir logs/automation_reports

echo.
echo 🎉 Automation reports generation completed!
echo 📁 JSON exports saved to: logs/automation_reports/
pause
