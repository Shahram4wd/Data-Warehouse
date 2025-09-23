@echo off
REM Comprehensive Docker management script for automation reports and CRM operations
REM This script provides a menu-driven interface for Docker-based operations

setlocal enabledelayedexpansion

:MENU
cls
echo ==========================================
echo  DATA WAREHOUSE - DOCKER OPERATIONS
echo ==========================================
echo.
echo  1. Generate Automation Reports (All CRMs)
echo  2. Generate Automation Reports (HubSpot only)
echo  3. Generate Automation Reports (Genius only)
echo  4. Generate Automation Reports (Arrivy only)
echo  5. Run Full CRM Sync + Reports
echo  6. Run HubSpot Sync
echo  7. Run Genius Sync
echo  8. Run Arrivy Sync
echo  9. View Recent Logs
echo  10. Check Docker Status
echo  11. Start Celery Worker
echo  12. Start Celery Beat (Scheduler)
echo  0. Exit
echo.
set /p choice="Enter your choice (0-12): "

if "%choice%"=="1" goto REPORTS_ALL
if "%choice%"=="2" goto REPORTS_HUBSPOT
if "%choice%"=="3" goto REPORTS_GENIUS
if "%choice%"=="4" goto REPORTS_ARRIVY
if "%choice%"=="5" goto SYNC_ALL
if "%choice%"=="6" goto SYNC_HUBSPOT
if "%choice%"=="7" goto SYNC_GENIUS
if "%choice%"=="8" goto SYNC_ARRIVY
if "%choice%"=="9" goto VIEW_LOGS
if "%choice%"=="10" goto DOCKER_STATUS
if "%choice%"=="11" goto START_WORKER
if "%choice%"=="12" goto START_BEAT
if "%choice%"=="0" goto EXIT
goto MENU

:REPORTS_ALL
echo.
echo Generating automation reports for all CRMs...
docker-compose exec web python manage.py generate_automation_reports --time-window 24 --detailed --crm all --export-json --output-dir logs/automation_reports
goto PAUSE_RETURN

:REPORTS_HUBSPOT
echo.
echo Generating automation reports for HubSpot...
docker-compose exec web python manage.py generate_automation_reports --time-window 24 --detailed --crm hubspot --export-json --output-dir logs/automation_reports
goto PAUSE_RETURN

:REPORTS_GENIUS
echo.
echo Generating automation reports for Genius...
docker-compose exec web python manage.py generate_automation_reports --time-window 24 --detailed --crm genius --export-json --output-dir logs/automation_reports
goto PAUSE_RETURN

:REPORTS_ARRIVY
echo.
echo Generating automation reports for Arrivy...
docker-compose exec web python manage.py generate_automation_reports --time-window 24 --detailed --crm arrivy --export-json --output-dir logs/automation_reports
goto PAUSE_RETURN

:SYNC_ALL
echo.
echo Running full CRM sync for all systems...
echo [1/4] HubSpot sync...
docker-compose exec web python manage.py sync_hubspot_all_new
echo [2/4] Genius sync...
docker-compose exec web python manage.py sync_genius_divisions ; docker-compose exec web python manage.py sync_genius_marketing_sources ; docker-compose exec web python manage.py sync_genius_users
echo [3/4] Arrivy sync...
docker-compose exec web python manage.py sync_arrivy_all
echo [4/4] Generating automation reports...
docker-compose exec web python manage.py generate_automation_reports --time-window 24 --detailed --crm all --export-json --output-dir logs/automation_reports
goto PAUSE_RETURN

:SYNC_HUBSPOT
echo.
echo Running HubSpot sync...
docker-compose exec web python manage.py sync_hubspot_all_new
goto PAUSE_RETURN

:SYNC_GENIUS
echo.
echo Running Genius sync...
docker-compose exec web python manage.py sync_genius_divisions
docker-compose exec web python manage.py sync_genius_marketing_sources
docker-compose exec web python manage.py sync_genius_users
goto PAUSE_RETURN

:SYNC_ARRIVY
echo.
echo Running Arrivy sync...
docker-compose exec web python manage.py sync_arrivy_all
goto PAUSE_RETURN

:VIEW_LOGS
echo.
echo Showing recent logs...
docker-compose logs web --tail=50
goto PAUSE_RETURN

:DOCKER_STATUS
echo.
echo Docker Compose Status:
docker-compose ps
echo.
echo Docker Images:
docker images | findstr data-warehouse
echo.
echo Docker Volumes:
docker volume ls | findstr data-warehouse
goto PAUSE_RETURN

:START_WORKER
echo.
echo Starting Celery Worker...
REM Use the dedicated celery service to avoid spawning extra workers in the web container
REM Concurrency is controlled in docker-compose.yml (e.g., --concurrency=2)
docker-compose up -d celery
echo Celery worker service started in background
goto PAUSE_RETURN

:START_BEAT
echo.
echo Starting Celery Beat Scheduler...
REM Use the dedicated celery-beat service rather than running inside the web container
docker-compose up -d celery-beat
echo Celery beat scheduler service started in background
echo This will run automation reports at 9:00 PM and 4:00 AM UTC daily
goto PAUSE_RETURN

:PAUSE_RETURN
echo.
pause
goto MENU

:EXIT
echo.
echo Goodbye!
endlocal
exit /b 0
