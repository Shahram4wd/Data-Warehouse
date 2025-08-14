"""
Custom exceptions for sync operations
"""
  
class SyncException(Exception):
    """Base exception for sync operations"""
    def __init__(self, message, details=None, retry_after=None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.retry_after = retry_after

class ConnectionException(SyncException):
    """Exception raised for connection issues (e.g., pool exhausted, network failure)"""
    def __init__(self, message, connection_name=None, **kwargs):
        super().__init__(message, **kwargs)
        self.connection_name = connection_name

class ValidationException(SyncException):
    """Exception raised during data validation"""
    def __init__(self, message, field_name=None, field_value=None, **kwargs):
        super().__init__(message, **kwargs)
        self.field_name = field_name
        self.field_value = field_value

class APIException(SyncException):
    """Exception raised during API operations"""
    def __init__(self, message, status_code=None, response_data=None, **kwargs):
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response_data = response_data

class APIClientException(APIException):
    """Exception raised by API client operations"""
    def __init__(self, message, endpoint=None, method=None, **kwargs):
        super().__init__(message, **kwargs)
        self.endpoint = endpoint
        self.method = method

class AuthenticationException(APIException):
    """Exception raised for authentication failures"""
    def __init__(self, message, **kwargs):
        super().__init__(message, status_code=401, **kwargs)

class DataSourceException(SyncException):
    """Exception raised for data source issues"""
    def __init__(self, message, source_name=None, **kwargs):
        super().__init__(message, **kwargs)
        self.source_name = source_name

class RateLimitException(APIException):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, message, retry_after=None, **kwargs):
        super().__init__(message, retry_after=retry_after, **kwargs)

class DatabaseException(SyncException):
    """Exception raised during database operations"""
    def __init__(self, message, query=None, **kwargs):
        super().__init__(message, **kwargs)
        self.query = query

class ConfigurationException(SyncException):
    """Exception raised for configuration issues"""
    def __init__(self, message, config_key=None, **kwargs):
        super().__init__(message, **kwargs)
        self.config_key = config_key

class RetryableException(SyncException):
    """Exception that indicates the operation should be retried"""
    def __init__(self, message, retry_count=0, max_retries=3, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_count = retry_count
        self.max_retries = max_retries
        
    def should_retry(self):
        return self.retry_count < self.max_retries

class NonRetryableException(SyncException):
    """Exception that indicates the operation should not be retried"""
    pass

class BulkOperationException(SyncException):
    """Exception raised during bulk operations"""
    def __init__(self, message, successful_count=0, failed_count=0, errors=None, **kwargs):
        super().__init__(message, **kwargs)
        self.successful_count = successful_count
        self.failed_count = failed_count
        self.errors = errors or []

class TransformationException(SyncException):
    """Exception raised during data transformation"""
    def __init__(self, message, input_data=None, transformation_step=None, **kwargs):
        super().__init__(message, **kwargs)
        self.input_data = input_data
        self.transformation_step = transformation_step
