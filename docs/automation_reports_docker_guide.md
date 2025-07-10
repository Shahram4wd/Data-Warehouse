# Automation Reports System - Docker Guide

This document explains how to use the automated reporting system for CRM operations in a Docker environment on Windows.

## Overview

The automation reports system generates comprehensive metrics and analytics for:
- **HubSpot CRM** - Contact, deal, and appointment sync operations
- **Genius CRM** - Division, marketing source, and user sync operations  
- **Arrivy** - Task, entity, and location report sync operations

## Quick Start

### 1. Test the System
```cmd
scripts\test_automation_reports_docker.bat
```

### 2. Generate Reports Manually
```cmd
# All CRMs
docker-compose exec web python manage.py generate_automation_reports --detailed --crm all --export-json

# Specific CRM
docker-compose exec web python manage.py generate_automation_reports --detailed --crm hubspot --export-json
```

### 3. Use the Interactive Menu
```cmd
scripts\docker_manager.bat
```

## Scheduled Execution

### Celery Configuration
The system is configured to automatically run automation reports:
- **9:00 PM UTC daily** (Evening report)
- **4:00 AM UTC daily** (Morning report)

### Starting the Scheduler
```cmd
# Start Celery worker (processes tasks)
docker-compose exec -d web celery -A data_warehouse worker --loglevel=info

# Start Celery beat (scheduler)
docker-compose exec -d web celery -A data_warehouse beat --loglevel=info
```

### Monitoring Scheduled Tasks
```cmd
# Check Celery status
docker-compose exec web celery -A data_warehouse inspect active

# View logs
docker-compose logs web -f
```

## Command Reference

### Management Command: `generate_automation_reports`

#### Basic Syntax
```cmd
docker-compose exec web python manage.py generate_automation_reports [options]
```

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--crm` | CRM to report on (`hubspot`, `genius`, `arrivy`, `all`) | `all` |
| `--time-window` | Hours of history to analyze | `24` |
| `--detailed` | Include detailed metrics | `False` |
| `--export-json` | Export to JSON files | `False` |
| `--output-dir` | JSON export directory | `logs/automation_reports` |
| `--force-sync` | Run sync before reports | `False` |

#### Examples
```cmd
# Basic report for all CRMs
docker-compose exec web python manage.py generate_automation_reports

# Detailed report with JSON export
docker-compose exec web python manage.py generate_automation_reports --detailed --export-json

# HubSpot only, last 12 hours
docker-compose exec web python manage.py generate_automation_reports --crm hubspot --time-window 12

# Force sync then generate reports
docker-compose exec web python manage.py generate_automation_reports --force-sync --detailed --export-json
```

## Scripts Reference

### Windows Batch Scripts

#### `docker_manager.bat`
Interactive menu for all Docker operations:
- Generate automation reports
- Run CRM syncs
- View logs
- Manage Celery workers

#### `run_automation_reports_docker.bat`
Dedicated script for generating automation reports with default settings.

#### `run_crm_sync_docker.bat [crm_name]`
Run sync operations for specific CRMs:
```cmd
scripts\run_crm_sync_docker.bat hubspot
scripts\run_crm_sync_docker.bat genius
scripts\run_crm_sync_docker.bat arrivy
scripts\run_crm_sync_docker.bat all
```

#### `test_automation_reports_docker.bat`
Validates that the automation reports system is working correctly.

## Output Files

### JSON Reports
When using `--export-json`, reports are saved to:
```
logs/automation_reports/
├── automation_report_hubspot_YYYYMMDD_HHMMSS.json
├── automation_report_genius_YYYYMMDD_HHMMSS.json
├── automation_report_arrivy_YYYYMMDD_HHMMSS.json
└── automation_report_consolidated_YYYYMMDD_HHMMSS.json
```

### Report Structure
Each JSON report contains:
```json
{
  "metadata": {
    "source": "hubspot",
    "report_generated_at": "2025-07-10T21:00:00Z",
    "time_window_hours": 24
  },
  "performance_metrics": {
    "total_actions": 150,
    "successful_actions": 147,
    "overall_success_rate": 0.98,
    "actions_per_hour": 6.25
  },
  "system_health": {
    "active_rules": 12,
    "total_rules": 15,
    "rule_utilization_rate": 0.8
  },
  "recommendations": [...]
}
```

## Troubleshooting

### Common Issues

#### Docker Services Not Running
```cmd
# Check status
docker-compose ps

# Start services
docker-compose up -d web db redis
```

#### Command Not Found
```cmd
# Check if management command exists
docker-compose exec web python manage.py help generate_automation_reports

# If missing, check installation
docker-compose exec web ls -la ingestion/management/commands/
```

#### Permission Errors
```cmd
# Create logs directory if missing
docker-compose exec web mkdir -p logs/automation_reports

# Check permissions
docker-compose exec web ls -la logs/
```

#### Celery Not Working
```cmd
# Check Celery worker status
docker-compose exec web celery -A data_warehouse inspect ping

# Restart worker
docker-compose restart web
docker-compose exec -d web celery -A data_warehouse worker --loglevel=info
```

### Debug Commands

#### View Recent Logs
```cmd
# Application logs
docker-compose logs web --tail=50

# Celery-specific logs
docker-compose logs web --tail=50 | findstr celery
```

#### Check Database Connection
```cmd
docker-compose exec web python manage.py check --database
```

#### Test Management Commands
```cmd
# List all available commands
docker-compose exec web python manage.py help

# Test specific CRM sync
docker-compose exec web python manage.py sync_hubspot_contacts_new --dry-run
```

## Integration with CI/CD

### Docker Compose Override
For production, create `docker-compose.override.yml`:
```yaml
version: '3.8'
services:
  web:
    volumes:
      - ./logs:/app/logs
    environment:
      - CELERY_ALWAYS_EAGER=False
  
  celery-worker:
    image: your-app:latest
    command: celery -A data_warehouse worker --loglevel=info
    depends_on:
      - db
      - redis
    environment:
      - DJANGO_SETTINGS_MODULE=data_warehouse.settings
  
  celery-beat:
    image: your-app:latest
    command: celery -A data_warehouse beat --loglevel=info
    depends_on:
      - db
      - redis
    environment:
      - DJANGO_SETTINGS_MODULE=data_warehouse.settings
```

### Monitoring
Set up external monitoring for the automation reports:
```cmd
# Health check endpoint (if implemented)
curl http://localhost:8000/api/health/automation-reports/

# Check report files
docker-compose exec web find logs/automation_reports -name "*.json" -mtime -1
```

## Best Practices

1. **Run tests first** - Always use `test_automation_reports_docker.bat` before production
2. **Monitor disk space** - JSON reports can accumulate; implement log rotation
3. **Check Celery regularly** - Ensure workers and beat scheduler are running
4. **Review reports** - Regularly check generated reports for system health
5. **Backup configurations** - Save Celery schedules and automation rules

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review application logs: `docker-compose logs web`
3. Test individual components with the provided scripts
4. Ensure all dependencies are properly configured in Docker
