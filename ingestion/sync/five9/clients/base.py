"""
Base Five9 API Client
Handles WSDL connections and authentication for Five9 Web Services
"""
import os
import requests
import zeep
from zeep import Transport
from requests.auth import HTTPBasicAuth
from django.conf import settings
from typing import Optional, Dict, Any
import logging

from ....config.five9_config import Five9Config

logger = logging.getLogger(__name__)


class BaseFive9Client:
    """Base Five9 API Client with WSDL connection management"""
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.username = username or os.getenv("FIVE9_USERNAME")
        self.password = password or os.getenv("FIVE9_PASSWORD")
        
        if not self.username or not self.password:
            raise ValueError("Five9 credentials not found in environment variables")
        
        self.auth = HTTPBasicAuth(self.username, self.password)
        self.transport = self._create_transport()
        self.admin_service = None
        self.supervisor_service = None
        
        # WSDL URLs
        encoded_username = self.username.replace('@', '%40')
        base_url = Five9Config.BASE_URL
        admin_path = Five9Config.ADMIN_WSDL_PATH
        supervisor_path = Five9Config.SUPERVISOR_WSDL_PATH
        
        self.admin_wsdl = f"{base_url}{admin_path}?wsdl&user={encoded_username}"
        self.supervisor_wsdl = f"{base_url}{supervisor_path}?wsdl&user={encoded_username}"
    
    def _create_transport(self) -> Transport:
        """Create authenticated transport for WSDL connections"""
        session = requests.Session()
        session.auth = self.auth
        return Transport(session=session)
    
    def connect(self) -> bool:
        """Connect to Five9 Web Services"""
        logger.info("Connecting to Five9 Web Services...")
        
        try:
            # Connect to Admin Service
            admin_client = zeep.Client(self.admin_wsdl, transport=self.transport)
            self.admin_service = admin_client.service
            logger.info("Admin Web Service connected successfully")
            
            # Connect to Supervisor Service
            supervisor_client = zeep.Client(self.supervisor_wsdl, transport=self.transport)
            self.supervisor_service = supervisor_client.service
            
            # Set session parameters using config
            session_params = {
                'forceLogoutSession': Five9Config.FORCE_LOGOUT_SESSION,
                'rollingPeriod': Five9Config.ROLLING_PERIOD,
                'statisticsRange': Five9Config.STATISTICS_RANGE,
                'shiftStart': Five9Config.SHIFT_START_HOUR * 60 * 60 * 1000,
                'timeZone': Five9Config.TIMEZONE_OFFSET_HOURS * 60 * 60 * 1000,
            }
            self.supervisor_service.setSessionParameters(session_params)
            logger.info("Supervisor Web Service connected successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Five9 Web Services: {e}")
            return False
    
    def clean_zeep_object(self, obj: Any) -> Any:
        """Convert Zeep objects to clean Python objects"""
        if hasattr(obj, '__values__'):
            cleaned = {}
            for key, value in obj.__values__.items():
                cleaned[key] = self.clean_zeep_object(value)
            return cleaned
        elif isinstance(obj, list):
            return [self.clean_zeep_object(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self.clean_zeep_object(v) for k, v in obj.items()}
        else:
            return obj
    
    def close_sessions(self):
        """Close Five9 sessions"""
        try:
            if self.admin_service:
                self.admin_service.closeSession()
            if self.supervisor_service:
                self.supervisor_service.closeSession()
            logger.info("Five9 sessions closed successfully")
        except Exception as e:
            logger.warning(f"Error closing Five9 sessions: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        if not self.connect():
            raise ConnectionError("Failed to connect to Five9 Web Services")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close_sessions()
