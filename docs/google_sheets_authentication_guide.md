# 🚀 Google Sheets Authentication & Setup Guide

## Quick Start (Recommended)

### 1. Get Google Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select a project
3. Enable **Google Sheets API** and **Google Drive API**
4. Create **OAuth 2.0 Client ID** (**Desktop application** - no redirect URIs needed)
5. Download `credentials.json` to project root

### 2. Pre-Authenticate (Run on Windows Host)

**⚠️ IMPORTANT: Run this on your Windows machine, NOT in Docker!**

#### Option A: Use the batch script (Easiest)
```cmd
# In Command Prompt/PowerShell, navigate to project directory
cd c:\projects\python\Data-Warehouse

# Run the setup script
scripts\setup_google_auth.bat
```

#### Option B: Manual steps
```cmd
# Install packages
pip install google-auth google-auth-oauthlib google-api-python-client

# Run pre-auth script (will auto-open browser)
python scripts/google_auth_setup.py
```

This automatically opens your browser, authenticates, and creates `token.json`.

### 3. Test in Docker

The token.json is automatically mounted into Docker:

```bash
# Test connection
docker-compose exec web python manage.py sync_gsheet_marketing_leads --test-connection
```

### 4. Run Sync

```bash
# Dry run (test without saving)
docker-compose exec web python manage.py sync_gsheet_marketing_leads --dry-run

# Full sync
docker-compose exec web python manage.py sync_gsheet_marketing_leads
```

## Detailed Setup Instructions

### OAuth2 Client Setup

#### 1. Create OAuth2 Client
1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth 2.0 Client IDs**
3. Choose **Desktop application** (this is important!)
4. **Name**: "Data Warehouse Google Sheets Integration"
5. Click **CREATE** (no redirect URIs needed for desktop apps)

#### 2. Download Credentials
1. Click the **Download** button (⬇️) next to your OAuth 2.0 Client ID
2. Save the file as `credentials.json` in your project root

#### 3. OAuth Consent Screen
1. Go to **APIs & Services** → **OAuth consent screen**
2. Choose **External** user type (for testing)
3. Fill required fields:
   - **App name**: "Data Warehouse Google Sheets Integration"
   - **User support email**: Your email
   - **Developer contact email**: Your email
4. Add your email to **Test users** section
5. **Save and Continue**

**Note**: Desktop applications use dynamic redirect URIs that are automatically handled by the OAuth2 library. No manual redirect URI configuration needed!

### Alternative: Service Account Setup

For production environments, you may prefer service account authentication:

#### 1. Create Service Account
1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **Service Account**
3. Fill in details:
   - Name: "data-warehouse-sheets-service"
   - Description: "Service account for Google Sheets access"
4. Skip role assignment (optional)
5. Click **Done**

#### 2. Generate Service Account Key
1. Click on the created service account
2. Go to **Keys** tab
3. Click **Add Key** → **Create new key**
4. Choose **JSON** format
5. Download and save as `service-account-key.json`

#### 3. Share Google Sheets with Service Account
1. Copy the service account email from the JSON file
2. Open your Google Sheet
3. Click **Share**
4. Add the service account email with **Viewer** or **Editor** access

#### 4. Update Environment Variables
Add to your `.env` file:
```bash
# Service Account Authentication (preferred)
GOOGLE_SERVICE_ACCOUNT_FILE=service-account-key.json

# OR OAuth2 Authentication
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json
```

## Authentication Methods

### OAuth2 Authentication (Recommended for Development)

Pre-authentication approach (simplest for Docker):

1. **Install Google packages on your host machine:**
   ```bash
   # In PowerShell/Command Prompt on your Windows machine
   pip install google-auth google-auth-oauthlib google-api-python-client
   ```

2. **Run pre-auth script on your host machine:**
   ```bash
   # Navigate to your project directory
   cd c:\projects\python\Data-Warehouse
   
   # Run the pre-authentication script (this will open your browser)
   python scripts/google_auth_setup.py
   ```
   This will:
   - Open your browser for OAuth2 authentication
   - Create `token.json` with valid credentials
   - Work seamlessly with Docker (files are auto-mounted)

3. **Start/restart Docker:**
   ```bash
   docker-compose up
   # or if already running:
   docker-compose restart web
   ```

4. **Test the connection in Docker:**
   ```bash
   docker-compose exec web python manage.py sync_gsheet_marketing_leads --test-connection
   ```

## Testing Authentication

### Test OAuth2:
```bash
docker-compose exec web python manage.py sync_gsheet_marketing_leads --test-connection
```

### Test Service Account:
```bash
# Set environment variable first
docker-compose exec web bash -c "export GOOGLE_SERVICE_ACCOUNT_FILE=service-account-key.json && python manage.py sync_gsheet_marketing_leads --test-connection"
```

## Troubleshooting

### OAuth2 Issues

#### 🚨 Desktop App OAuth2 Fix

**Problem**: Getting error: "This site can't be reached" or redirect URI issues

**Root Cause**: Desktop applications don't use static redirect URIs. The OAuth2 library automatically handles this.

**Solution**:

1. **Verify OAuth2 Client Type**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - **APIs & Services** → **Credentials**
   - Check your **OAuth 2.0 Client ID**
   - **Application type** should be: **Desktop application**
   - If it says "Web application", create a new one as Desktop application

2. **No Redirect URIs Needed**
   - Desktop applications don't have "Authorized redirect URIs" section
   - The OAuth2 library automatically finds an available port
   - If you see redirect URI errors, you likely have a Web application instead of Desktop

3. **Run Pre-Auth Script**
   ```cmd
   # In PowerShell/Command Prompt on Windows
   cd c:\projects\python\Data-Warehouse
   python scripts/google_auth_setup.py
   ```

**Key Points**:
- ✅ **Desktop application** = No redirect URIs needed  
- ❌ **Web application** = Requires redirect URIs (not what we want)

#### Other OAuth2 Issues:
- **Port conflict (WinError 10048)**: Stop Docker temporarily with `docker-compose down`, run auth script, then restart Docker
- **Error 400: invalid_request**: Ensure you created a Desktop application (not Web application)
- **Access denied**: Add your email to test users in OAuth consent screen
- **App not verified**: Publish the app or use service account authentication
- **Missing credentials.json**: Download from Google Console
- **Token expired**: Re-run `python scripts/google_auth_setup.py`

### Service Account Issues:
- **Permission denied**: Share the sheet with service account email
- **File not found**: Check service account JSON file path
- **Invalid scope**: Ensure APIs are enabled

### General Issues:
- **Permission denied**: Share your Google Sheet with your Google account
- **API not enabled**: Enable Google Sheets API and Google Drive API

## Prerequisites

Before running the pre-auth script, ensure you have:

1. **Google Cloud Project** with APIs enabled:
   - Google Sheets API
   - Google Drive API

2. **OAuth2 Credentials** configured correctly:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - **APIs & Services** → **Credentials**
   - Create **OAuth 2.0 Client ID** (**Desktop application** - no redirect URIs needed)
   - Download as `credentials.json`

## Security Notes

- **Never commit** `credentials.json` or `service-account-key.json` to version control
- Add these files to `.gitignore`
- Use environment variables for file paths
- For production, use service accounts with minimal required permissions
- OAuth2 tokens are stored securely in `token.json`
- All data is retrieved read-only
- No sensitive data is logged (except in debug mode)
- SSL/TLS encryption for all API communications

## File Structure

After successful setup, you should have:

```
c:\projects\python\Data-Warehouse\
├── credentials.json          # OAuth2 credentials (from Google Console)
├── token.json               # Generated after authentication
├── service-account-key.json # Optional: for service account auth
└── .env                     # Environment variables
```

✅ **Files are auto-mounted from host to Docker - no manual copying needed!**

## Integration with Data Warehouse

This authentication setup works with the Data Warehouse Google Sheets integration, which includes:

- ✅ OAuth2 authentication with Google
- ✅ Delta sync based on sheet modification time
- ✅ Full sync history tracking using SyncHistory model
- ✅ Comprehensive error handling and validation
- ✅ Support for multiple sheets/tabs
- ✅ Auto-detection of column headers
- ✅ Raw data preservation in JSON format

The updated scripts now use the default OAuth2 flow which automatically handles port selection and callbacks for desktop applications.
