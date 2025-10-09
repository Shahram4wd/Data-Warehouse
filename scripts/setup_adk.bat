@echo off
REM DataHub ADK Quick Setup Script for Windows
REM This script helps automate the GCP and ADK setup process

echo === DataHub Google ADK Setup ===
echo.

REM Check if gcloud is installed
where gcloud >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: gcloud CLI is not installed
    echo Please install it from: https://cloud.google.com/sdk/docs/install
    exit /b 1
)

echo [OK] gcloud CLI is installed
echo.

REM Check and switch account if needed
echo Checking current account...
gcloud config get-value account
echo.
set /p SWITCH_ACCOUNT="Login with different account? (y/N): "
if /i "%SWITCH_ACCOUNT%"=="y" (
    echo Opening browser for account login...
    gcloud auth login
    echo.
)

REM Get project ID
set /p PROJECT_ID="Enter GCP Project ID [datahub]: "
if "%PROJECT_ID%"=="" set PROJECT_ID=datahub

echo Using project: %PROJECT_ID%
echo.

REM Set current project
echo Setting current project...
gcloud config set project %PROJECT_ID%
echo [OK] Project set
echo.

REM Get region
set /p REGION="Enter region [us-west1]: "
if "%REGION%"=="" set REGION=us-west1

echo.
echo Enabling required APIs...

REM Enable required APIs
echo Enabling aiplatform.googleapis.com...
gcloud services enable aiplatform.googleapis.com --project=%PROJECT_ID%
echo [OK] aiplatform.googleapis.com enabled

echo Enabling run.googleapis.com...
gcloud services enable run.googleapis.com --project=%PROJECT_ID%
echo [OK] run.googleapis.com enabled

echo Enabling cloudbuild.googleapis.com...
gcloud services enable cloudbuild.googleapis.com --project=%PROJECT_ID%
echo [OK] cloudbuild.googleapis.com enabled

echo.
echo Setting up service account...

REM Create service account
set SERVICE_ACCOUNT=datahub-adk
set SERVICE_ACCOUNT_EMAIL=%SERVICE_ACCOUNT%@%PROJECT_ID%.iam.gserviceaccount.com

echo Creating service account...
gcloud iam service-accounts create %SERVICE_ACCOUNT% --display-name="DataHub ADK Service Account" --project=%PROJECT_ID% 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Service account created
) else (
    echo [OK] Service account already exists
)

REM Grant permissions
echo Granting permissions...
gcloud projects add-iam-policy-binding %PROJECT_ID% --member="serviceAccount:%SERVICE_ACCOUNT_EMAIL%" --role="roles/aiplatform.user" --quiet
echo [OK] Permissions granted

REM Create credentials directory
echo.
echo Creating credentials directory...
if not exist .google mkdir .google

REM Create and download credentials
echo Downloading service account credentials...
gcloud iam service-accounts keys create .google\credentials.json --iam-account=%SERVICE_ACCOUNT_EMAIL% --project=%PROJECT_ID%
echo [OK] Credentials saved to .google\credentials.json

REM Update .env file
echo.
echo Updating .env file...

if not exist .env (
    echo Error: .env file not found
    exit /b 1
)

REM Check if GOOGLE_CLOUD_PROJECT exists in .env
findstr /C:"GOOGLE_CLOUD_PROJECT" .env >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] .env file already has Google Cloud configuration
) else (
    echo. >> .env
    echo # Google ADK Configuration for DataHub AI Agents >> .env
    echo GOOGLE_CLOUD_PROJECT=%PROJECT_ID% >> .env
    echo GOOGLE_CLOUD_LOCATION=%REGION% >> .env
    echo GOOGLE_GENAI_USE_VERTEXAI=True >> .env
    echo GOOGLE_APPLICATION_CREDENTIALS=/app/.google/credentials.json >> .env
    echo [OK] .env file updated
)

REM Set application default credentials
echo.
echo Setting up application default credentials...
echo Please complete the authentication in your browser...
gcloud auth application-default login

echo [OK] Application default credentials set

echo.
echo === Setup Complete! ===
echo.
echo Next steps:
echo 1. Build Docker containers: docker-compose build
echo 2. Start services: docker-compose up -d
echo 3. Access ADK web UI: http://localhost:7860
echo.
echo Configuration:
echo   Project ID: %PROJECT_ID%
echo   Region: %REGION%
echo   Credentials: .google\credentials.json
echo.
echo For more information, see docs\AI\SETUP_GUIDE.md
echo.
pause
