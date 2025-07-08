# Data Warehouse - Enterprise CRM Integration Platform

A Django-based data warehouse platform with enterprise-grade CRM integrations, featuring advanced monitoring, automation, and scalability.

## Features

### Core Platform
- **Django Framework**: Robust web application framework
- **RESTful APIs**: Comprehensive API endpoints for data access
- **Database Management**: Advanced ORM with migration support
- **Task Management**: Celery-based asynchronous processing
- **Containerization**: Docker and Docker Compose support

### Enterprise CRM Integration
- **HubSpot Integration**: Full-featured enterprise-grade integration
- **Multi-CRM Support**: Extensible architecture for multiple CRM systems
- **Real-time Sync**: Bidirectional data synchronization
- **Advanced Monitoring**: Comprehensive dashboard and alerting
- **Connection Pooling**: Optimized resource management
- **Encryption**: Secure credential and data handling

### Advanced Features
- **Monitoring Dashboard**: Real-time sync status and performance metrics
- **Alert System**: Proactive notifications for issues and anomalies
- **Automation Engine**: Intelligent workflow automation
- **Retry Logic**: Robust error handling and recovery
- **Rate Limiting**: API quota management and optimization
- **Validation**: Comprehensive data validation and cleaning

## Architecture

The platform follows a modular, enterprise-ready architecture:

```
data_warehouse/          # Core Django application
├── ingestion/          # Data ingestion modules
│   ├── base/          # Enterprise base classes
│   ├── monitoring/    # Monitoring and alerting
│   ├── sync/          # CRM sync engines
│   └── management/    # Django management commands
├── reports/           # Reporting functionality
└── templates/         # Web interface templates
```

## Getting Started

### Prerequisites
- Python 3.8+
- Django 4.0+
- PostgreSQL (recommended)
- Redis (for Celery)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Start the development server:
   ```bash
   python manage.py runserver
   ```

### Docker Deployment

```bash
docker-compose up -d
```

## Configuration

### Environment Variables
- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Redis connection for Celery
- `HUBSPOT_API_KEY`: HubSpot API credentials
- `DEBUG`: Debug mode (development only)

### Enterprise Features
Initialize enterprise features:
```bash
python manage.py init_enterprise_features
```

Test HubSpot integration:
```bash
python manage.py test_hubspot_sync
```

## Usage

### Web Interface
Access the monitoring dashboard at `/monitoring/dashboard/`

### API Endpoints
- `/api/sync/status/` - Sync status information
- `/api/monitoring/metrics/` - Performance metrics
- `/api/alerts/` - Alert management

### Management Commands
- `sync_hubspot_contacts` - Sync HubSpot contacts
- `sync_hubspot_deals` - Sync HubSpot deals
- `sync_hubspot_appointments` - Sync HubSpot appointments
- `sync_hubspot_divisions` - Sync HubSpot divisions

## Development

### Project Structure
See `docs/import_refactoring.md` for detailed architecture documentation.

### Testing
```bash
python manage.py test
```

### Contributing
1. Follow the enterprise architecture patterns
2. Ensure comprehensive error handling
3. Add monitoring and logging
4. Update documentation

## Deployment

### Production Deployment
Use the enterprise deployment script:
```bash
python deploy_enterprise_features.py
```

### Monitoring
The platform includes comprehensive monitoring:
- Real-time sync status
- Performance metrics
- Error tracking
- Alert notifications

## Documentation

- `docs/import_refactoring.md` - Architecture and implementation details
- `CLEANUP_SUMMARY.md` - Project cleanup and file organization

## License

[Add your license information here]

## Support

[Add support information here]
