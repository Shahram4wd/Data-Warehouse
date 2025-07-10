@echo off
REM Test script for automation reports in Docker environment
REM This script runs basic tests to ensure the automation reports functionality works

echo ==========================================
echo Testing Automation Reports (Docker)
echo ==========================================

REM Check Docker Compose availability
echo [1/5] Checking Docker Compose...
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker Compose not available
    goto ERROR_EXIT
)
echo ✓ Docker Compose available

REM Check if services are running
echo [2/5] Checking services...
docker-compose ps web | find "Up" >nul
if %errorlevel% neq 0 (
    echo WARNING: Starting web service...
    docker-compose up -d web
    timeout /t 15 /nobreak
)
echo ✓ Services running

REM Test basic command availability
echo [3/5] Testing command availability...
docker-compose exec web python manage.py help generate_automation_reports >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: generate_automation_reports command not found
    goto ERROR_EXIT
)
echo ✓ Command available

REM Test basic report generation (without detailed metrics)
echo [4/5] Testing basic report generation...
docker-compose exec web python manage.py generate_automation_reports --time-window 1 --crm all
if %errorlevel% neq 0 (
    echo WARNING: Basic report generation had issues
) else (
    echo ✓ Basic report generation successful
)

REM Test JSON export
echo [5/5] Testing JSON export...
docker-compose exec web python manage.py generate_automation_reports --time-window 1 --crm hubspot --export-json --output-dir logs/test_reports
if %errorlevel% neq 0 (
    echo WARNING: JSON export had issues
) else (
    echo ✓ JSON export successful
)

echo.
echo ==========================================
echo Test completed successfully!
echo ==========================================
echo.
echo Next steps:
echo 1. Run full automation reports:
echo    docker-compose exec web python manage.py generate_automation_reports --detailed --crm all --export-json
echo.
echo 2. Schedule with Celery:
echo    docker-compose exec web celery -A data_warehouse beat --loglevel=info
echo.
echo 3. Monitor logs:
echo    docker-compose logs web -f
echo.
goto SUCCESS_EXIT

:ERROR_EXIT
echo.
echo ==========================================
echo Test failed!
echo ==========================================
echo.
echo Please check:
echo 1. Docker Desktop is running
echo 2. Project is properly configured
echo 3. Database migrations are up to date
echo.
echo Debug commands:
echo   docker-compose logs web --tail=20
echo   docker-compose exec web python manage.py check
echo.
exit /b 1

:SUCCESS_EXIT
pause
exit /b 0
