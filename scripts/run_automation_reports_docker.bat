@echo off
REM Windows batch script to run automation reports in Docker
REM This script is designed for Windows environments using Docker Compose

echo ==========================================
echo Automation Reports Generator (Docker)
echo ==========================================

REM Check if Docker Compose is available
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker Compose is not available
    echo Please make sure Docker Desktop is running
    exit /b 1
)

REM Check if the web service is running
docker-compose ps web | find "Up" >nul
if %errorlevel% neq 0 (
    echo WARNING: Web service may not be running
    echo Starting services...
    docker-compose up -d web
    timeout /t 10 /nobreak
)

echo.
echo Running automation reports generation...
echo.

REM Run the automation reports command in Docker
docker-compose exec web python manage.py generate_automation_reports ^ 
    --time-window 24 ^
    --detailed ^
    --crm all ^
    --export-json ^
    --output-dir logs/automation_reports

if %errorlevel% equ 0 (
    echo.
    echo ==========================================
    echo Automation reports generated successfully!
    echo ==========================================
    echo.
    echo Reports saved to: logs/automation_reports/
    echo.
    echo To view reports:
    echo   docker-compose exec web ls -la logs/automation_reports/
    echo.
    echo To copy reports to host:
    echo   docker cp container_name:/app/logs/automation_reports/ ./reports/
) else (
    echo.
    echo ==========================================
    echo ERROR: Automation reports generation failed
    echo ==========================================
    echo.
    echo Check the logs for more information:
    echo   docker-compose logs web
)

pause
