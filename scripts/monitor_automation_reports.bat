@echo off
REM Monitoring script for Automation Reports system
REM Provides real-time status and health checks

setlocal enabledelayedexpansion

:MAIN_LOOP
cls
echo ==========================================
echo  AUTOMATION REPORTS - SYSTEM MONITOR
echo ==========================================
echo.
echo Current Time: %date% %time%
echo.

REM Check Docker services
echo [DOCKER SERVICES]
docker-compose ps --format "table {{.Name}}\t{{.State}}\t{{.Status}}" 2>nul
if %errorlevel% neq 0 (
    echo ❌ Docker Compose not available or services not running
    goto ERROR_STATUS
)

echo.

REM Check Celery worker status
echo [CELERY STATUS]
docker-compose exec web celery -A data_warehouse inspect ping 2>nul | find "pong" >nul
if %errorlevel% equ 0 (
    echo ✅ Celery Worker: Running
) else (
    echo ❌ Celery Worker: Not responding
)

REM Check for recent automation reports
echo.
echo [RECENT REPORTS]
docker-compose exec web find logs/automation_reports -name "*.json" -mtime -1 2>nul | head -5
if %errorlevel% neq 0 (
    echo ⚠️  No recent reports found (last 24 hours)
) else (
    echo ✅ Recent reports available
)

REM Check last execution from logs
echo.
echo [RECENT ACTIVITY]
docker-compose logs web --tail=10 2>nul | findstr /i "automation\|celery\|generate_automation_reports"

REM Show scheduled tasks
echo.
echo [NEXT SCHEDULED RUNS]
echo ⏰ Evening Report: 9:00 PM UTC daily
echo ⏰ Morning Report: 4:00 AM UTC daily

echo.
echo ==========================================
echo Options:
echo   [R] Refresh  [T] Test  [L] Logs  [Q] Quit
echo ==========================================
set /p choice="Enter choice: "

if /i "%choice%"=="r" goto MAIN_LOOP
if /i "%choice%"=="t" goto TEST_SYSTEM
if /i "%choice%"=="l" goto VIEW_LOGS
if /i "%choice%"=="q" goto EXIT
goto MAIN_LOOP

:TEST_SYSTEM
echo.
echo Running quick test...
docker-compose exec web python manage.py generate_automation_reports --time-window 1 --crm hubspot
echo.
pause
goto MAIN_LOOP

:VIEW_LOGS
echo.
echo Showing last 30 log lines (press Ctrl+C to return to menu)...
docker-compose logs web --tail=30 -f
goto MAIN_LOOP

:ERROR_STATUS
echo.
echo ❌ System appears to be down
echo.
echo Troubleshooting steps:
echo 1. Start services: docker-compose up -d
echo 2. Check status: docker-compose ps
echo 3. View logs: docker-compose logs web
echo.
pause
goto MAIN_LOOP

:EXIT
echo.
echo Monitoring stopped.
endlocal
exit /b 0
