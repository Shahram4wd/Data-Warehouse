from datetime import datetime
import os
import logging
import psycopg2
import mysql.connector
from django.db import transaction

logger = logging.getLogger(__name__)

def parse_datetime_obj(value):
    """Convert common date/datetime formats to datetime objects.
       Returns None if parsing fails or input is empty.
       Assumes parsed datetime is naive UTC.
    """
    if not value or not str(value).strip():
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None

def process_batches(to_create, to_update, model_class, update_fields, batch_size):
    """Process batches for bulk_create and bulk_update."""
    if to_update:
        with transaction.atomic():
            model_class.objects.bulk_update(to_update, update_fields)
        to_update.clear()

    if to_create:
        with transaction.atomic():
            model_class.objects.bulk_create(to_create, ignore_conflicts=True)
        to_create.clear()

def fetch_data_from_db(table_name, db_host, db_name, db_user, db_password):
    """Fetch data from an external database table."""
    try:
        connection = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password
        )
        cursor = connection.cursor()

        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]

        return rows, column_names

    except Exception as e:
        raise RuntimeError(f"Error fetching data from table '{table_name}': {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()

def prepare_data(row, field_mapping, required_fields):
    """Prepare data for model creation or update from a CSV row."""
    data = {}
    for csv_field, model_field in field_mapping.items():
        value = row.get(csv_field)
        if csv_field in required_fields and not value:
            return None  # Skip rows with missing required fields
        data[model_field] = value
    return data

def get_mysql_connection():
    """
    Establish and return a connection to the MySQL database using environment variables.
    Includes retry logic, connection timeout settings, and fallback hosts.
    """
    import time
    import mysql.connector.errors
    
    db_host = os.getenv("GENIUS_DB_HOST")
    db_name = os.getenv("GENIUS_DB_NAME") 
    db_user = os.getenv("GENIUS_DB_USER")
    db_password = os.getenv("GENIUS_DB_PASSWORD")
    db_port = int(os.getenv("GENIUS_DB_PORT", 3306))  # Default to 3306 if not set

    if not all([db_host, db_name, db_user, db_password]):
        raise ValueError("Database connection details are missing in environment variables.")

    # Fallback hosts to try if primary host fails
    fallback_hosts = [
        db_host,  # Primary host
        "db2.nsginternal.com",  # Original host as fallback
        "localhost",  # Local fallback if available
    ]
    
    # Remove duplicates while preserving order
    hosts_to_try = []
    for host in fallback_hosts:
        if host and host not in hosts_to_try:
            hosts_to_try.append(host)

    # Connection configuration with timeouts and retry settings
    base_config = {
        'database': db_name,
        'user': db_user,
        'password': db_password,
        'port': db_port,
        'connection_timeout': 10,  # 10 seconds connection timeout
        'autocommit': True,
        'charset': 'utf8mb4',
        'collation': 'utf8mb4_unicode_ci'
    }
    
    # Try each host
    for host in hosts_to_try:
        config = base_config.copy()
        config['host'] = host
        
        max_retries = 2  # Reduced retries per host
        retry_delay = 3  # seconds
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to MySQL database at {host}:{db_port} (attempt {attempt + 1}/{max_retries})")
                connection = mysql.connector.connect(**config)
                logger.info(f"Successfully connected to MySQL database at {host}:{db_port}")
                return connection
                
            except mysql.connector.errors.DatabaseError as e:
                error_code = getattr(e, 'errno', 'Unknown')
                # Special handling for expired password (MySQL error 1862)
                if error_code == 1862:
                    logger.error(
                        "MySQL error 1862: Password expired. Please reset the MySQL user's password. "
                        "Suggested fix: \n"
                        "  1. Log into MySQL with an admin account.\n"
                        f"  2. ALTER USER '{db_user}'@'%' IDENTIFIED BY '<NewStrongPassword>';\n"
                        f"  3. (If required) ALTER USER '{db_user}'@'%' PASSWORD EXPIRE NEVER;\n"
                        "  4. Update ENV variable GENIUS_DB_PASSWORD (and any secret stores).\n"
                        "  5. Rebuild/restart the container: docker-compose restart web worker."
                    )
                logger.warning(f"Database connection to {host} attempt {attempt + 1} failed (Error {error_code}): {e}")
                if attempt < max_retries - 1 and error_code != 1862:
                    # Only retry if not a fatal (non-recoverable) condition like password expired
                    logger.info(f"Retrying connection to {host} in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"All {max_retries} connection attempts to {host} failed")
                    break  # Try next host
                    
            except Exception as e:
                logger.warning(f"Unexpected error connecting to {host} attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying connection to {host} in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"All {max_retries} connection attempts to {host} failed")
                    break  # Try next host
    
    # If we reach here, all hosts failed
    logger.error(f"Failed to connect to any of the available MySQL hosts: {hosts_to_try}")
    raise mysql.connector.errors.DatabaseError("Unable to connect to any MySQL database host")


def get_athena_connection():
    """
    Create and return an Athena client using boto3.
    This replaces the pyathena connection approach.
    """
    from ingestion.athena_client import get_athena_client
    return get_athena_client()


def get_athena_client():
    """
    Establish and return an Athena client using boto3 and environment variables.
    """
    from ingestion.athena_client import AthenaClient
    
    # Get AWS credentials and configuration from environment variables
    aws_access_key_id = os.getenv("SALESPRO_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("SALESPRO_SECRETE_ACCESS_KEY")
    region_name = os.getenv("SALESPRO_SERVER_REGION", "us-east-1")
    s3_staging_dir = os.getenv("SALESPRO_S3_LOCATION")

    if not all([aws_access_key_id, aws_secret_access_key, s3_staging_dir]):
        raise ValueError("AWS Athena connection details are missing in environment variables.")
    
    return AthenaClient(
        region=region_name,
        aws_key=aws_access_key_id,
        aws_secret=aws_secret_access_key,
        s3_output=s3_staging_dir,
        workgroup='primary',
        database='default'
    )
