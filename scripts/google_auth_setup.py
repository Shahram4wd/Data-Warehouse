#!/usr/bin/env python3
"""
Google Sheets Pre-Authentication Script

Run this on your host machine (with browser access) to generate token.json
Then mount the token into Docker for seamless authentication.

Usage:
    python scripts/google_auth_setup.py
"""
import os
import sys
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Same scopes as the main application
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

def main():
    """Pre-authenticate with Google and save token for Docker use"""
    
    print("🔐 Google Sheets Pre-Authentication Setup")
    print("=" * 50)
    
    # File paths
    credentials_file = 'credentials.json'
    token_file = 'token.json'
    
    # Check if credentials file exists
    if not os.path.exists(credentials_file):
        print(f"❌ Error: {credentials_file} not found")
        print("\nPlease:")
        print("1. Go to Google Cloud Console")
        print("2. Create OAuth 2.0 Client ID (Desktop application)")
        print("3. Download credentials.json to project root")
        print("4. See docs/google_auth_setup.md for detailed instructions")
        return False
    
    # Check if Docker is running on port 8080 and suggest stopping it
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port_in_use = sock.connect_ex(('localhost', 8080)) == 0
    sock.close()
    
    if port_in_use:
        print("⚠️  Port 8080 is in use (likely Docker). For best results:")
        print("   docker-compose down")
        print("   Then run this script again.")
        print("   Continuing anyway with automatic port selection...")
        print("")
    
    creds = None
    
    # Load existing token if available
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        print(f"📄 Found existing token: {token_file}")
    
    # If no valid credentials, run OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("🔄 Refreshing expired token...")
                creds.refresh(Request())
                print("✅ Token refreshed successfully")
            except Exception as e:
                print(f"⚠️  Token refresh failed: {e}")
                creds = None
        
        if not creds:
            print("🌐 Starting OAuth2 flow...")
            print("Your browser will open automatically for authentication")
            print("")
            print("ℹ️  Using desktop application OAuth2 flow (no redirect URIs needed)")
            print("")
            
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            
            # Use default OAuth flow for desktop applications with automatic port selection
            try:
                # Don't specify a port - let the library find an available one
                # This avoids conflicts with Docker's port 8080
                creds = flow.run_local_server(
                    port=0,  # 0 = automatically find available port
                    open_browser=True
                )
                print("✅ OAuth2 authentication completed")
            except Exception as e:
                print(f"❌ OAuth2 authentication failed: {e}")
                print("")
                print("💡 Troubleshooting:")
                print("1. Ensure credentials.json is for a 'Desktop application' (not Web application)")
                print("2. Check that Google Sheets API and Google Drive API are enabled")
                print("3. Make sure your OAuth consent screen is configured")
                print("4. If using external user type, add your email as a test user")
                print("5. Try stopping Docker if it's using port 8080: docker-compose down")
                raise
    
    # Save the credentials for Docker use
    with open(token_file, 'w') as token:
        token.write(creds.to_json())
    
    print(f"💾 Saved authentication token: {token_file}")
    print("\n🐳 Docker Setup:")
    print("Now you can run Docker with the pre-authenticated token:")
    print(f"  docker-compose up  # token.json will be automatically mounted")
    print("\n✅ Setup complete! Your Docker container can now access Google Sheets.")
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Authentication cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure credentials.json is valid")
        print("2. Check Google Console OAuth configuration")
        print("3. Enable Google Sheets API and Google Drive API")
        print("4. See docs/google_auth_setup.md for help")
        sys.exit(1)
