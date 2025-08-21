import os
from pathlib import Path
from decouple import config, Csv
import dj_database_url
from dotenv import load_dotenv
import logging.handlers

# Custom Rotating File Handler that puts the number before the extension
class CustomRotatingFileHandler(logging.handlers.RotatingFileHandler):
    def rotation_filename(self, default_name):
        """
        Modify the filename of a log file when rotating.
        
        This changes the default behavior from filename.log.1 to filename.1.log
        
        :param default_name: The default name for the log file.
        """
        if not callable(self.namer):
            result = default_name
        else:
            result = self.namer(default_name)
        
        # Custom logic to put number before extension
        import re
        match = re.match(r'(.+)\.([^.]+)\.(\d+)$', result)
        if match:
            filename, ext, number = match.groups()
            result = f"{filename}.{number}.{ext}"
        
        return result

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = config('DJANGO_SECRET_KEY')
DEBUG = config('DEBUG', cast=bool)

ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", cast=Csv())

# Installed apps
INSTALLED_APPS = [
    # Django built-in apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Custom apps
    'ingestion',
    'reports',  # Add reports app here
    
    # Third-party apps
    'django_celery_beat',
    'rest_framework',
    'drf_spectacular',
    'explorer',  # SQL Explorer as a separate app
]

# Add DRF settings
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Spectacular settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'Data Warehouse API',
    'DESCRIPTION': 'API for syncing and managing data warehouse data',
    'VERSION': '1.0.0',
}

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add WhiteNoise middleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'ingestion.middleware.WordPressBlockerMiddleware',  # Add this
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'data_warehouse.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # Add this line to specify the templates directory
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'data_warehouse.wsgi.application'

# Database
DATABASE_URL = os.getenv("DATABASE_URL")

DATABASES = {
    "default": dj_database_url.config(
        default=DATABASE_URL, 
        conn_max_age=1800,
        conn_health_checks=True,  # Add health checks
    ),
}

# Add database connection pooling for production
if not DEBUG:
    DATABASES['default']['OPTIONS'] = {
        'MAX_CONNS': 20,
        'MIN_CONNS': 1,
    }

# Configure PostgreSQL schema search path for Django tables separation
if DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
    if 'OPTIONS' not in DATABASES['default']:
        DATABASES['default']['OPTIONS'] = {}

    # Set search path to include all necessary schemas
    search_path = 'django,orchestration,monitoring,ingestion,report'
    
    # Add schema search path to connection options
    if 'options' in DATABASES['default']['OPTIONS']:
        existing_options = DATABASES['default']['OPTIONS']['options']
        DATABASES['default']['OPTIONS']['options'] = f"{existing_options} -c search_path={search_path}"
    else:
        DATABASES['default']['OPTIONS']['options'] = f'-c search_path={search_path}'

# Password validation (optional for dev)
AUTH_PASSWORD_VALIDATORS = []

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'  # Changed from 'staticfiles/' to standard '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Add STATIC_ROOT setting
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'  # Use WhiteNoise for static files

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    'https://data-warehouse-57lg.onrender.com',
    'https://latenightcode.com',  # No trailing slash
    'https://www.latenightcode.com',  # Add www variant
    'http://localhost:8000',
    'http://127.0.0.1:8000',  # Add 127.0.0.1 variant
    'http://0.0.0.0:8000',    # Add docker variant
]

# CORS settings if you're using django-cors-headers
CORS_ALLOWED_ORIGINS = [
    'https://data-warehouse-57lg.onrender.com',
    'https://latenightcode.com',
    'https://www.latenightcode.com',
    'http://localhost:8000',
    'http://127.0.0.1:8000',  # Add 127.0.0.1 variant
    'http://0.0.0.0:8000',    # Add docker variant
]

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# SQL Explorer Configuration
EXPLORER_CONNECTIONS = {'Default': 'default'}
EXPLORER_DEFAULT_CONNECTION = 'default'
EXPLORER_DB_CONNECTIONS_ENABLED = True
EXPLORER_USER_UPLOADS_ENABLED = True

EXPLORER_PERMISSION_VIEW = lambda r: r.user.is_staff
EXPLORER_PERMISSION_CHANGE = lambda r: r.user.is_staff

# Only show tables that start with "ingestion_"
EXPLORER_SCHEMA_INCLUDE_TABLE_PREFIXES = ['ingestion_']
# Exclude tables that start with "explorer_"
EXPLORER_SCHEMA_EXCLUDE_TABLE_PREFIXES = ['explorer_']

EXPLORER_SQL_BLACKLIST = (
     # DML
     'COMMIT',
     'DELETE',
     'INSERT',
     'MERGE',
     'REPLACE',
     'ROLLBACK',
     'SET',
     'START',
     'UPDATE',
     'UPSERT',

     # DDL
     'ALTER',
     'CREATE',
     'DROP',
     'RENAME',
     'TRUNCATE',

     # DCL
     'GRANT',
     'REVOKE',
 )

# Genius API Configuration
GENIUS_API_URL = config("GENIUS_API_URL")
GENIUS_USERNAME = config("GENIUS_USERNAME")
GENIUS_PASSWORD = config("GENIUS_PASSWORD")

# HubSpot API Configuration
HUBSPOT_API_TOKEN = config("HUBSPOT_API_TOKEN", default="")

# ActiveProspect API Configuration  
ACTIVEPROSPECT_API_TOKEN = config("ACTIVEPROSPECT_API_TOKEN", default="")
ACTIVEPROSPECT_USERNAME = config("ACTIVEPROSPECT_USERNAME", default="X")
ACTIVEPROSPECT_PASSWORD = config("ACTIVEPROSPECT_PASSWORD", default="")
ACTIVEPROSPECT_BASE_URL = config("ACTIVEPROSPECT_BASE_URL", default="https://app.leadconduit.com")

# MarketSharp API Configuration
MARKETSHARP_SECRET_KEY = config("MARKETSHARP_SECRET_KEY", default="")
MARKETSHARP_API_URL = config("MARKETSHARP_API_URL", default="")
MARKETSHARP_API_KEY = config("MARKETSHARP_API_KEY", default="")
MARKETSHARP_COMPANY_ID = config("MARKETSHARP_COMPANY_ID", default="")

# Arrivy API Configuration
ARRIVY_API_KEY = config("ARRIVY_API_KEY", default="")
ARRIVY_AUTH_KEY = config("ARRIVY_AUTH_KEY", default="")
ARRIVY_API_URL = config("ARRIVY_API_URL", default="")

# Genius Database Configuration
GENIUS_DB_HOST = config("GENIUS_DB_HOST", default="")
GENIUS_DB_NAME = config("GENIUS_DB_NAME", default="")
GENIUS_DB_USER = config("GENIUS_DB_USER", default="")
GENIUS_DB_PASSWORD = config("GENIUS_DB_PASSWORD", default="")

# SalesRabbit API Configuration
SALESRABBIT_API_TOKEN = config('SALESRABBIT_API_TOKEN', default='')
SALESRABBIT_API_URL = config('SALESRABBIT_API_URL', default='https://api.salesrabbit.com')

# Redirect users to SQL Explorer after login
LOGIN_REDIRECT_URL = '/explorer/'  # Set SQL Explorer as the default page after login

# Redirect unauthenticated users to the login page
LOGIN_URL = '/accounts/login/'

# Create logs directory
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Add logging configuration to track performance issues
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'ingestion_file': {
            'level': 'DEBUG',
            'class': 'data_warehouse.settings.CustomRotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'ingestion.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'reports_file': {
            'level': 'DEBUG',
            'class': 'data_warehouse.settings.CustomRotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'reports.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'general_file': {
            'level': 'INFO',
            'class': 'data_warehouse.settings.CustomRotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'general.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'connection_pool_file': {
            'level': 'DEBUG',
            'class': 'data_warehouse.settings.CustomRotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'connection_pool.log'),
            'maxBytes': 5 * 1024 * 1024,  # 5MB
            'backupCount': 3,
            'formatter': 'verbose',
        },
        'sync_engines_file': {
            'level': 'DEBUG',
            'class': 'data_warehouse.settings.CustomRotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'sync_engines.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'general_file'],
        'level': 'INFO',
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console', 'general_file'],
            'level': 'WARNING',  # Only log slow queries
            'propagate': False,
        },
        'ingestion': {
            'handlers': ['console', 'ingestion_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'ingestion.base.connection_pool': {
            'handlers': ['console', 'connection_pool_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'ingestion.sync': {
            'handlers': ['console', 'sync_engines_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'ingestion.sync.hubspot': {
            'handlers': ['console', 'sync_engines_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'ingestion.sync.genius': {
            'handlers': ['console', 'sync_engines_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'reports': {
            'handlers': ['console', 'reports_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'ingestion_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['console', 'general_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Optimize for production
if not DEBUG:
    # Reduce worker timeout issues
    DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB
    FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB
    
    # Cache configuration
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
            'TIMEOUT': 300,
            'OPTIONS': {
                'MAX_ENTRIES': 1000,
            }
        }
    }
