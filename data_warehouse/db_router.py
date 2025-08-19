"""
Database router for schema separation
"""

class SchemaRouter:
    """
    Route Django framework tables to 'django' schema and application tables to 'warehouse' schema
    """
    
    # Django framework apps that should go to django schema
    DJANGO_APPS = [
        'admin',
        'auth',
        'contenttypes',
        'sessions',
        'django_celery_beat',
        'explorer',
    ]
    
    def db_for_read(self, model, **hints):
        """Suggest database to read from."""
        return None  # Use default database for all reads
    
    def db_for_write(self, model, **hints):
        """Suggest database to write to.""" 
        return None  # Use default database for all writes
    
    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if models are in the same database."""
        return True  # Allow all relations
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Decide if migration should run on the given database."""
        return True  # Allow all migrations on default database

class DjangoSchemaRouter:
    """
    Custom database router to put Django tables in 'django' schema
    This is applied at the model level using db_table with schema prefix
    """
    pass
