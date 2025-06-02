from datetime import datetime
import os
import psycopg2
import mysql.connector
from django.db import transaction

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
    """
    db_host = os.getenv("GENIUS_DB_HOST")
    db_name = os.getenv("GENIUS_DB_NAME")
    db_user = os.getenv("GENIUS_DB_USER")
    db_password = os.getenv("GENIUS_DB_PASSWORD")
    db_port = os.getenv("GENIUS_DB_PORT", 3306)  # Default to 3306 if not set

    if not all([db_host, db_name, db_user, db_password]):
        raise ValueError("Database connection details are missing in environment variables.")

    return mysql.connector.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password,
        port=db_port
    )
