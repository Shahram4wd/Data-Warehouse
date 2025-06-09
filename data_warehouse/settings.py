import os
from pathlib import Path
from decouple import config, Csv
import dj_database_url
from dotenv import load_dotenv

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
]

# CORS settings if you're using django-cors-headers
CORS_ALLOWED_ORIGINS = [
    'https://data-warehouse-57lg.onrender.com',
    'https://latenightcode.com',
    'https://www.latenightcode.com',
    'http://localhost:8000',
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

# Redirect users to SQL Explorer after login
LOGIN_REDIRECT_URL = '/explorer/'  # Set SQL Explorer as the default page after login

# Add logging configuration to track performance issues
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',  # Only log slow queries
            'propagate': False,
        },
        'ingestion': {
            'handlers': ['console'],
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
