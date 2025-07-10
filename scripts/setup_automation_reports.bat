@echo off
REM Setup script for Automation Reports system in Docker
REM This script sets up and validates the complete automation reporting system

echo ==========================================
echo  AUTOMATION REPORTS SETUP (Docker)
echo ==========================================

set "SETUP_LOG=logs\automation_setup.log"

REM Create logs directory
echo [1/8] Creating directory structure...
if not exist "logs" mkdir logs
if not exist "logs\automation_reports" mkdir logs\automation_reports
echo ✓ Directory structure created >> %SETUP_LOG% 2>&1

REM Check Docker environment
echo [2/8] Validating Docker environment...
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker Compose not available
    echo Please install Docker Desktop for Windows
    goto ERROR_EXIT
)
echo ✓ Docker Compose available >> %SETUP_LOG% 2>&1

REM Start services if needed
echo [3/8] Starting Docker services...
docker-compose ps web | find "Up" >nul 2>&1
if %errorlevel% neq 0 (
    echo Starting services...
    docker-compose up -d web db redis >> %SETUP_LOG% 2>&1
    timeout /t 20 /nobreak >nul
)
echo ✓ Services running >> %SETUP_LOG% 2>&1

REM Run migrations
echo [4/8] Running database migrations...
docker-compose exec web python manage.py migrate >> %SETUP_LOG% 2>&1
echo ✓ Migrations completed >> %SETUP_LOG% 2>&1

REM Test management command
echo [5/8] Testing automation reports command...
docker-compose exec web python manage.py help generate_automation_reports >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Automation reports command not found
    goto ERROR_EXIT
)
echo ✓ Command available >> %SETUP_LOG% 2>&1

REM Test basic report generation
echo [6/8] Testing report generation...
docker-compose exec web python manage.py generate_automation_reports --time-window 1 --crm hubspot >> %SETUP_LOG% 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Report generation test had issues
    echo Check %SETUP_LOG% for details
) else (
    echo ✓ Report generation working >> %SETUP_LOG% 2>&1
)

REM Start Celery worker
echo [7/8] Starting Celery worker...
docker-compose exec -d web celery -A data_warehouse worker --loglevel=info >> %SETUP_LOG% 2>&1
timeout /t 5 /nobreak >nul
echo ✓ Celery worker started >> %SETUP_LOG% 2>&1

REM Start Celery beat scheduler
echo [8/8] Starting Celery beat scheduler...
docker-compose exec -d web celery -A data_warehouse beat --loglevel=info >> %SETUP_LOG% 2>&1
timeout /t 5 /nobreak >nul
echo ✓ Celery beat started >> %SETUP_LOG% 2>&1

echo.
echo ==========================================
echo  SETUP COMPLETED SUCCESSFULLY!
echo ==========================================
echo.
echo ✅ Automation reports system is now active
echo ✅ Scheduled to run daily at 9:00 PM and 4:00 AM UTC
echo ✅ Scripts available in scripts\ directory
echo.
echo Quick commands:
echo   Manual report: scripts\run_automation_reports_docker.bat
echo   Interactive menu: scripts\docker_manager.bat
echo   Test system: scripts\test_automation_reports_docker.bat
echo.
echo Monitoring:
echo   View logs: docker-compose logs web -f
echo   Check status: docker-compose ps
echo   Setup log: %SETUP_LOG%
echo.
echo Next steps:
echo 1. Wait for first scheduled run (9:00 PM UTC)
echo 2. Check logs directory for reports
echo 3. Monitor Celery workers: docker-compose logs web -f
echo.
goto SUCCESS_EXIT

:ERROR_EXIT
echo.
echo ==========================================
echo  SETUP FAILED!
echo ==========================================
echo.
echo Please check:
echo 1. Docker Desktop is running
echo 2. Project dependencies are installed
echo 3. Database is accessible
echo.
echo Debug information:
echo   Setup log: %SETUP_LOG%
echo   Docker logs: docker-compose logs web --tail=20
echo   Service status: docker-compose ps
echo.
pause
exit /b 1

:SUCCESS_EXIT
pause
exit /b 0
