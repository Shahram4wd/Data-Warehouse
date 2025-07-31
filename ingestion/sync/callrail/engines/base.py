"""
Base sync engine for CallRail CRM integration following the CRM sync guide architecture
"""
import logging
from typing import Dict, Any, List, Optional
from ingestion.base.sync_engine import BaseSyncEngine

logger = logging.getLogger(__name__)


class CallRailBaseSyncEngine(BaseSyncEngine):
    """Base sync engine for CallRail with common functionality"""
    
    def __init__(self, **kwargs):
        """
        Initialize CallRail sync engine
        
        Args:
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(crm_source='callrail', sync_type='callrail', **kwargs)
        
    def get_default_batch_size(self) -> int:
        """Return default batch size for CallRail sync"""
        return 100
        
    async def initialize_client(self) -> None:
        """Initialize the CallRail API client"""
        # This will be implemented by subclasses
        pass
        
    async def fetch_data(self, **kwargs):
        """Fetch data from CallRail API - implemented by subclasses"""
        # This will be implemented by subclasses
        yield []
        
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform CallRail data - implemented by subclasses"""
        return raw_data
        
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate CallRail data - implemented by subclasses"""
        return data
        
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save CallRail data - implemented by subclasses"""
        return {'created': 0, 'updated': 0}
        
    async def cleanup(self) -> None:
        """Cleanup CallRail sync resources"""
        pass
        
    def get_sync_params(self) -> Dict[str, Any]:
        """Get parameters for sync operation"""
        return {
            'dry_run': getattr(self, 'dry_run', False),
            'force': getattr(self, 'force', False),
        }
