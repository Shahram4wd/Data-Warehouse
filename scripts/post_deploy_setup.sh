#!/bin/bash
# Post-deployment script for Render.com to setup cron jobs properly

echo "🚀 Running post-deployment setup for cron jobs..."

# Check environment
echo "Checking environment variables..."
echo "DJANGO_ENV: $DJANGO_ENV"

# Run migrations to ensure django_celery_beat tables exist
echo "Running database migrations..."
python manage.py migrate

# Enable production periodic tasks
echo "Enabling production periodic tasks..."
python manage.py enable_production_tasks

# Verify tasks are properly configured
echo "Final verification of periodic tasks..."
python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
import os
print('Environment: %s' % os.environ.get('DJANGO_ENV', 'NOT SET'))
print('Production tasks:')
for task in PeriodicTask.objects.filter(name__contains='automation-reports'):
    print('- %s: %s (enabled: %s)' % (task.name, task.crontab, task.enabled))
"

echo "✅ Post-deployment setup completed!"
