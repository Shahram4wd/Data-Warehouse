"""
Enterprise features compatibility layer for graceful degradation
"""
import logging

logger = logging.getLogger(__name__)

class MockCredentialManager:
    """Mock credential manager for when enterprise features are not available"""
    
    def __init__(self):
        self.available = False
        
    async def initialize(self):
        pass
        
    async def get_credentials(self, source):
        return {}
        
    def is_healthy(self):
        return True

class MockAutomationEngine:
    """Mock automation engine for when enterprise features are not available"""
    
    def __init__(self, source):
        self.source = source
        self.available = False
        
    async def initialize(self):
        pass
        
    async def cleanup(self):
        pass
        
    async def handle_error(self, error, context):
        pass
        
    async def report_metrics(self, metrics):
        pass
        
    def is_healthy(self):
        return True

class MockAlertSystem:
    """Mock alert system for when enterprise features are not available"""
    
    def __init__(self):
        self.available = False
        
    async def initialize(self):
        pass
        
    async def cleanup(self):
        pass
        
    async def send_alert(self, alert_type, message, context=None, severity='info'):
        pass
        
    def is_healthy(self):
        return True

def get_credential_manager():
    """Get credential manager with fallback"""
    try:
        from ingestion.base.encryption import CredentialManager
        return CredentialManager()
    except ImportError as e:
        logger.warning(f"Enterprise encryption module not available: {e}")
        return MockCredentialManager()

def get_automation_engine(source):
    """Get automation engine with fallback"""
    try:
        from ingestion.base.automation import AutomationEngine
        return AutomationEngine(source)
    except ImportError as e:
        logger.warning(f"Enterprise automation module not available: {e}")
        return MockAutomationEngine(source)

def get_alert_system():
    """Get alert system with fallback"""
    try:
        from ingestion.monitoring.alerts import AlertSystem
        return AlertSystem()
    except ImportError as e:
        logger.warning(f"Enterprise monitoring module not available: {e}")
        return MockAlertSystem()
