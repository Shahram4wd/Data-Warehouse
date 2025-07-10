@echo off
REM Windows batch script to run CRM sync operations in Docker
REM Usage: run_crm_sync_docker.bat [crm_name]
REM   crm_name: hubspot, genius, arrivy, or all (default: all)

setlocal enabledelayedexpansion

set CRM_NAME=%1
if "%CRM_NAME%"=="" set CRM_NAME=all

echo ==========================================
echo CRM Sync Operations (Docker) - %CRM_NAME%
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
echo Running %CRM_NAME% sync operations...
echo.

if /i "%CRM_NAME%"=="hubspot" (
    echo Running HubSpot sync...
    docker-compose exec web python manage.py sync_hubspot_all_new
) else if /i "%CRM_NAME%"=="genius" (
    echo Running Genius sync...
    docker-compose exec web python manage.py sync_genius_divisions
    docker-compose exec web python manage.py sync_genius_marketing_sources
    docker-compose exec web python manage.py sync_genius_users
) else if /i "%CRM_NAME%"=="arrivy" (
    echo Running Arrivy sync...
    docker-compose exec web python manage.py sync_arrivy_all
) else if /i "%CRM_NAME%"=="all" (
    echo Running ALL CRM syncs...
    echo.
    echo [1/3] HubSpot sync...
    docker-compose exec web python manage.py sync_hubspot_all_new
    echo.
    echo [2/3] Genius sync...
    docker-compose exec web python manage.py sync_genius_divisions ; docker-compose exec web python manage.py sync_genius_marketing_sources ; docker-compose exec web python manage.py sync_genius_users
    echo.
    echo [3/3] Arrivy sync...
    docker-compose exec web python manage.py sync_arrivy_all
) else (
    echo ERROR: Invalid CRM name "%CRM_NAME%"
    echo Valid options: hubspot, genius, arrivy, all
    exit /b 1
)

if %errorlevel% equ 0 (
    echo.
    echo ==========================================
    echo %CRM_NAME% sync completed successfully!
    echo ==========================================
    echo.
    echo Now generating automation reports...
    echo.
    docker-compose exec web python manage.py generate_automation_reports --time-window 24 --detailed --crm %CRM_NAME% --export-json
    echo.
    echo To view sync logs:
    echo   docker-compose logs web --tail=100
) else (
    echo.
    echo ==========================================
    echo ERROR: %CRM_NAME% sync failed
    echo ==========================================
    echo.
    echo Check the logs for more information:
    echo   docker-compose logs web --tail=50
)

endlocal
pause
