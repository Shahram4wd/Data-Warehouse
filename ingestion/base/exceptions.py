"""
Custom exceptions for sync operations
"""

class SyncException(Exception):
    """Base exception for sync operations"""
    pass

class ValidationException(SyncException):
    """Exception raised during data validation"""
    pass

class APIException(SyncException):
    """Exception raised during API operations"""
    pass

class RateLimitException(APIException):
    """Exception raised when rate limit is exceeded"""
    pass

class DatabaseException(SyncException):
    """Exception raised during database operations"""
    pass

class ConfigurationException(SyncException):
    """Exception raised for configuration issues"""
    pass
