"""
AWS Athena client utility using boto3
Replaces pyathena dependency for SalesPro data operations
"""
import boto3
import time
import os
from typing import List, Dict, Any, Optional, Tuple
from botocore.exceptions import ClientError, NoCredentialsError
import logging

logger = logging.getLogger(__name__)


class AthenaClient:
    """AWS Athena client for querying SalesPro data"""
    
    def __init__(self, region: str = None, aws_key: str = None, aws_secret: str = None, 
                 s3_output: str = None, workgroup: str = "primary", database: str = "home_genius_db"):
        """
        Initialize Athena client with AWS credentials and configuration
        
        Args:
            region: AWS region name
            aws_key: AWS access key ID
            aws_secret: AWS secret access key
            s3_output: S3 location for query results
            workgroup: Athena workgroup name
            database: Default database name
        """
        # Use provided values or fall back to environment variables
        self.region = region or os.getenv("SALESPRO_SERVER_REGION", "us-east-1")
        self.aws_key = aws_key or os.getenv("SALESPRO_ACCESS_KEY_ID")
        self.aws_secret = aws_secret or os.getenv("SALESPRO_SECRETE_ACCESS_KEY")
        s3_base = os.getenv("SALESPRO_S3_LOCATION", "s3://customer-analytics-data-vault-staging/production/HomeGenius/")
        self.s3_output = s3_output or f"{s3_base}athena-results/"
        self.workgroup = workgroup
        self.database = database
        
        # Validate required configuration
        if not all([self.aws_key, self.aws_secret, self.s3_output]):
            raise ValueError("AWS Athena configuration is incomplete. Check environment variables.")
        
        # Ensure S3 output location ends with /
        if not self.s3_output.endswith('/'):
            self.s3_output += '/'
        
        # Initialize boto3 client
        self.client = boto3.client(
            "athena",
            region_name=self.region,
            aws_access_key_id=self.aws_key,
            aws_secret_access_key=self.aws_secret
        )
        
        logger.info(f"Athena client initialized for region {self.region}, workgroup {self.workgroup}")
    
    def run_query(self, query: str, database: str = None, timeout: int = 300) -> Optional[List[List[str]]]:
        """
        Execute an Athena query and return results
        
        Args:
            query: SQL query string
            database: Database name (uses default if not provided)
            timeout: Maximum wait time in seconds
            
        Returns:
            List of rows, where each row is a list of string values
            Returns None if query fails
        """
        db_name = database or self.database
        
        try:
            logger.info(f"Executing Athena query on database '{db_name}': {query[:100]}...")
            
            # Start query execution
            response = self.client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={"Database": db_name},
                ResultConfiguration={"OutputLocation": self.s3_output},
                WorkGroup=self.workgroup
            )
            
            query_execution_id = response["QueryExecutionId"]
            logger.info(f"Query started with execution ID: {query_execution_id}")
            
            # Wait for completion
            start_time = time.time()
            while True:
                if time.time() - start_time > timeout:
                    logger.error(f"Query timeout after {timeout} seconds")
                    return None
                
                status_response = self.client.get_query_execution(QueryExecutionId=query_execution_id)
                state = status_response["QueryExecution"]["Status"]["State"]
                
                if state == "SUCCEEDED":
                    logger.info("Query completed successfully")
                    break
                elif state in ["FAILED", "CANCELLED"]:
                    error_reason = status_response["QueryExecution"]["Status"].get("StateChangeReason", "Unknown error")
                    
                    # Check for specific permission errors and provide helpful guidance
                    if "glue:GetDatabase" in error_reason and "not authorized" in error_reason:
                        logger.error(f"AWS Glue permissions error: {error_reason}")
                        logger.error("SOLUTION: The IAM user needs 'glue:GetDatabase' permission. See docs/aws_athena_permissions_troubleshooting.md for detailed instructions.")
                    elif "Insufficient permissions" in error_reason:
                        logger.error(f"AWS permissions error: {error_reason}")
                        logger.error("SOLUTION: Check IAM permissions for the user. See docs/aws_iam_policy_for_athena.json for required permissions.")
                    else:
                        logger.error(f"Athena query {state.lower()}: {error_reason}")
                    return None
                elif state in ["QUEUED", "RUNNING"]:
                    logger.debug(f"Query status: {state}")
                    time.sleep(2)
                else:
                    logger.warning(f"Unknown query state: {state}")
                    time.sleep(2)
            
            # Fetch results
            return self._fetch_query_results(query_execution_id)
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            # Check for specific AWS errors and provide helpful guidance
            if error_code == 'AccessDenied' or 'glue:GetDatabase' in error_message:
                logger.error(f"AWS Glue permissions error [{error_code}]: {error_message}")
                logger.error("SOLUTION: The IAM user needs AWS Glue permissions. See docs/aws_athena_permissions_troubleshooting.md for setup instructions.")
            elif error_code in ['InvalidUserPoolConfigurationException', 'UnauthorizedOperation']:
                logger.error(f"AWS authorization error [{error_code}]: {error_message}")
                logger.error("SOLUTION: Check IAM permissions. See docs/aws_iam_policy_for_athena.json for required policy.")
            else:
                logger.error(f"AWS Athena error [{error_code}]: {error_message}")
            return None
        except NoCredentialsError:
            logger.error("AWS credentials not found or invalid")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error executing Athena query: {e}")
            return None
    
    def _fetch_query_results(self, query_execution_id: str) -> List[List[str]]:
        """
        Fetch results for a completed query with pagination support
        
        Args:
            query_execution_id: The execution ID of the completed query
            
        Returns:
            List of rows, where each row is a list of string values
        """
        try:
            rows = []
            next_token = None
            
            while True:
                # Get query results with pagination
                if next_token:
                    results = self.client.get_query_results(
                        QueryExecutionId=query_execution_id,
                        NextToken=next_token
                    )
                else:
                    results = self.client.get_query_results(QueryExecutionId=query_execution_id)
                
                result_set = results.get("ResultSet", {})
                result_rows = result_set.get("Rows", [])
                
                # Skip header row only on first page
                start_index = 1 if next_token is None else 0
                
                # Process rows
                for row_data in result_rows[start_index:]:
                    row = []
                    for col in row_data.get("Data", []):
                        # Extract value from column data
                        value = col.get("VarCharValue", "")
                        row.append(value)
                    rows.append(row)
                
                # Check for more pages
                next_token = results.get("NextToken")
                if not next_token:
                    break
            
            logger.info(f"Retrieved {len(rows)} rows from Athena query")
            return rows
            
        except ClientError as e:
            logger.error(f"Error fetching query results: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error fetching query results: {e}")
            return []
    
    def get_query_with_columns(self, query: str, database: str = None, timeout: int = 300) -> Tuple[Optional[List[str]], Optional[List[List[str]]]]:
        """
        Execute an Athena query and return both column names and data
        
        Args:
            query: SQL query string
            database: Database name (uses default if not provided)
            timeout: Maximum wait time in seconds
            
        Returns:
            Tuple of (column_names, rows) or (None, None) if query fails
        """
        db_name = database or self.database
        
        try:
            logger.info(f"Executing Athena query with columns on database '{db_name}': {query[:100]}...")
            
            # Start query execution
            response = self.client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={"Database": db_name},
                ResultConfiguration={"OutputLocation": self.s3_output},
                WorkGroup=self.workgroup
            )
            
            query_execution_id = response["QueryExecutionId"]
            
            # Wait for completion
            start_time = time.time()
            while True:
                if time.time() - start_time > timeout:
                    logger.error(f"Query timeout after {timeout} seconds")
                    return None, None
                
                status_response = self.client.get_query_execution(QueryExecutionId=query_execution_id)
                state = status_response["QueryExecution"]["Status"]["State"]
                
                if state == "SUCCEEDED":
                    break
                elif state in ["FAILED", "CANCELLED"]:
                    error_reason = status_response["QueryExecution"]["Status"].get("StateChangeReason", "Unknown error")
                    
                    # Check for specific permission errors and provide helpful guidance
                    if "glue:GetDatabase" in error_reason and "not authorized" in error_reason:
                        logger.error(f"AWS Glue permissions error: {error_reason}")
                        logger.error("SOLUTION: The IAM user needs 'glue:GetDatabase' permission. See docs/aws_athena_permissions_troubleshooting.md for detailed instructions.")
                    elif "Insufficient permissions" in error_reason:
                        logger.error(f"AWS permissions error: {error_reason}")
                        logger.error("SOLUTION: Check IAM permissions for the user. See docs/aws_iam_policy_for_athena.json for required permissions.")
                    else:
                        logger.error(f"Athena query {state.lower()}: {error_reason}")
                    return None, None
                elif state in ["QUEUED", "RUNNING"]:
                    time.sleep(2)
                else:
                    time.sleep(2)
            
            # Fetch results with column information
            return self._fetch_query_results_with_columns(query_execution_id)
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            # Check for specific AWS errors and provide helpful guidance
            if error_code == 'AccessDenied' or 'glue:GetDatabase' in error_message:
                logger.error(f"AWS Glue permissions error [{error_code}]: {error_message}")
                logger.error("SOLUTION: The IAM user needs AWS Glue permissions. See docs/aws_athena_permissions_troubleshooting.md for setup instructions.")
            elif error_code in ['InvalidUserPoolConfigurationException', 'UnauthorizedOperation']:
                logger.error(f"AWS authorization error [{error_code}]: {error_message}")
                logger.error("SOLUTION: Check IAM permissions. See docs/aws_iam_policy_for_athena.json for required policy.")
            else:
                logger.error(f"AWS Athena error [{error_code}]: {error_message}")
            return None, None
        except NoCredentialsError:
            logger.error("AWS credentials not found or invalid")
            return None, None
        except Exception as e:
            logger.exception(f"Error executing Athena query with columns: {e}")
            return None, None
    
    def _fetch_query_results_with_columns(self, query_execution_id: str) -> Tuple[List[str], List[List[str]]]:
        """
        Fetch results and column names for a completed query with pagination support
        
        Args:
            query_execution_id: The execution ID of the completed query
            
        Returns:
            Tuple of (column_names, rows)
        """
        try:
            column_names = []
            rows = []
            next_token = None
            first_page = True
            
            while True:
                # Get query results with pagination
                if next_token:
                    results = self.client.get_query_results(
                        QueryExecutionId=query_execution_id,
                        NextToken=next_token
                    )
                else:
                    results = self.client.get_query_results(QueryExecutionId=query_execution_id)
                
                result_set = results.get("ResultSet", {})
                result_rows = result_set.get("Rows", [])
                
                if not result_rows:
                    break
                
                # Extract column names from the first row of the first page
                if first_page:
                    header_row = result_rows[0]
                    for col in header_row.get("Data", []):
                        column_name = col.get("VarCharValue", "")
                        column_names.append(column_name)
                    
                    # Process data rows starting from index 1 (skip header)
                    data_rows = result_rows[1:]
                    first_page = False
                else:
                    # Process all rows on subsequent pages
                    data_rows = result_rows
                
                # Extract data rows
                for row_data in data_rows:
                    row = []
                    for col in row_data.get("Data", []):
                        value = col.get("VarCharValue", "")
                        row.append(value)
                    rows.append(row)
                
                # Check for more pages
                next_token = results.get("NextToken")
                if not next_token:
                    break
            
            logger.info(f"Retrieved {len(column_names)} columns and {len(rows)} rows from Athena query")
            return column_names, rows
            
        except Exception as e:
            logger.exception(f"Error fetching query results with columns: {e}")
            return [], []
    
    def test_connection(self) -> bool:
        """
        Test the Athena connection by running a simple query
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            test_query = "SELECT 1 as test_column"
            result = self.run_query(test_query, timeout=30)
            
            if result is not None and len(result) > 0:
                logger.info("Athena connection test successful")
                return True
            else:
                logger.error("Athena connection test failed - no results")
                return False
                
        except Exception as e:
            logger.exception(f"Athena connection test failed: {e}")
            return False


def get_athena_client() -> AthenaClient:
    """
    Factory function to create and return an AthenaClient instance
    Uses environment variables for configuration
    
    Returns:
        Configured AthenaClient instance
    """
    return AthenaClient()


def run_athena_query(query: str, database: str = "default", s3_output: str = None, 
                    region: str = None, aws_key: str = None, aws_secret: str = None, 
                    workgroup: str = "primary") -> Optional[List[List[str]]]:
    """
    Convenience function to run a single Athena query
    Compatible with the original function signature from the user's example
    
    Args:
        query: SQL query string
        database: Database name
        s3_output: S3 location for query results
        region: AWS region
        aws_key: AWS access key ID
        aws_secret: AWS secret access key
        workgroup: Athena workgroup name
        
    Returns:
        List of rows or None if query fails
    """
    client = AthenaClient(
        region=region,
        aws_key=aws_key,
        aws_secret=aws_secret,
        s3_output=s3_output,
        workgroup=workgroup,
        database=database
    )
    
    return client.run_query(query, database)
