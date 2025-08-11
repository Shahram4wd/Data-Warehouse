@echo off
echo.
echo ================================================================================
echo   Google Sheets Pre-Authentication Setup (Windows)
echo ================================================================================
echo.
echo This script will:
echo 1. Install required Google packages
echo 2. Run OAuth2 authentication in your browser
echo 3. Create token.json for Docker use
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause >nul
echo.

echo [1/3] Installing Google authentication packages...
pip install google-auth google-auth-oauthlib google-api-python-client
if %errorlevel% neq 0 (
    echo.
    echo ❌ Failed to install packages. Please check your Python/pip installation.
    echo.
    pause
    exit /b 1
)

echo.
echo [2/3] Running OAuth2 authentication...
echo Your browser will open automatically.
echo.
python scripts/google_auth_setup.py
if %errorlevel% neq 0 (
    echo.
    echo ❌ Authentication failed. Please check:
    echo - credentials.json exists in project root
    echo - Google Cloud APIs are enabled
    echo - OAuth consent screen is configured
    echo.
    pause
    exit /b 1
)

echo.
echo [3/3] Testing Docker integration...
echo.
docker-compose exec web python manage.py sync_gsheet_marketing_leads --test-connection
if %errorlevel% neq 0 (
    echo.
    echo ❌ Docker test failed. Please restart Docker containers:
    echo docker-compose restart web
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo ✅ SUCCESS! Google Sheets authentication is now configured.
echo.
echo You can now run sync commands in Docker:
echo   docker-compose exec web python manage.py sync_gsheet_marketing_leads --dry-run
echo   docker-compose exec web python manage.py sync_gsheet_marketing_leads
echo ================================================================================
echo.
pause
