"""
Deployment script for enterprise features
"""
import os
import sys
import subprocess
import asyncio
from pathlib import Path

def run_command(command, description):
    """Run a shell command with description"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ {description} completed")
            return True
        else:
            print(f"✗ {description} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ {description} failed: {e}")
        return False

def main():
    """Main deployment function"""
    print("🚀 Starting Enterprise Features Deployment")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Error: manage.py not found. Please run this script from the project root.")
        sys.exit(1)
    
    # Steps to deploy enterprise features
    steps = [
        ("pip install -r requirements.txt", "Installing Python dependencies"),
        ("python manage.py makemigrations", "Creating database migrations"),
        ("python manage.py migrate", "Running database migrations"),
        ("python manage.py collectstatic --noinput", "Collecting static files"),
        ("python manage.py init_enterprise_features", "Initializing enterprise features"),
    ]
    
    success_count = 0
    for command, description in steps:
        if run_command(command, description):
            success_count += 1
        else:
            print(f"❌ Deployment failed at step: {description}")
            print("Please check the error above and try again.")
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print(f"✅ All {len(steps)} deployment steps completed successfully")
    print("\nNext steps:")
    print("1. Start the development server: python manage.py runserver")
    print("2. Access the monitoring dashboard: http://localhost:8000/monitoring/")
    print("3. Run the integration tests: python test_enterprise_integration.py")
    print("4. Test a sync operation: python manage.py sync_hubspot_contacts --dry-run")
    
    print("\n📚 Documentation:")
    print("- Enterprise Integration Guide: docs/enterprise_integration_guide.md")
    print("- Standards Document: docs/import_refactoring.md")
    print("- API Documentation: http://localhost:8000/api/docs/")
    
    print("\n🔍 Health Check:")
    print("- System Health: http://localhost:8000/monitoring/api/health/")
    print("- Connection Status: http://localhost:8000/monitoring/api/data/?type=connections")

if __name__ == "__main__":
    main()
