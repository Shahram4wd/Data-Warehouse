from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ActiveProspectProcessor:
    """Base processor for ActiveProspect data processing"""
    
    @staticmethod
    def process_timestamp(timestamp_ms: Optional[int]) -> Optional[datetime]:
        """Convert millisecond timestamp to datetime"""
        if timestamp_ms is None:
            return None
        try:
            return datetime.fromtimestamp(timestamp_ms / 1000.0)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert timestamp {timestamp_ms}: {e}")
            return None
    
    @staticmethod
    def clean_string(value: Any, max_length: Optional[int] = None) -> Optional[str]:
        """Clean and truncate string values"""
        if value is None:
            return None
        
        str_value = str(value).strip()
        if not str_value:
            return None
            
        if max_length and len(str_value) > max_length:
            str_value = str_value[:max_length]
            logger.warning(f"String truncated to {max_length} chars: {str_value[:50]}...")
            
        return str_value
    
    @staticmethod
    def safe_decimal(value: Any, default=None):
        """Safely convert value to decimal"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Failed to convert to decimal: {value}")
            return default
    
    @staticmethod
    def safe_int(value: Any, default=None):
        """Safely convert value to integer"""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Failed to convert to int: {value}")
            return default
    
    @staticmethod
    def safe_bool(value: Any, default=False):
        """Safely convert value to boolean"""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)


class EventProcessor(ActiveProspectProcessor):
    """Processor for ActiveProspect Event data"""
    
    @classmethod
    def process_event(cls, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw event data into model fields"""
        logger.debug(f"Processing event: {event_data.get('id', 'unknown')}")
        
        # Core fields
        processed = {
            'id': cls.clean_string(event_data.get('id'), 50),
            'outcome': cls.clean_string(event_data.get('outcome'), 50),
            'reason': cls.clean_string(event_data.get('reason')),
            'event_type': cls.clean_string(event_data.get('type'), 50),
            'host': cls.clean_string(event_data.get('host'), 255),
        }
        
        # Timing fields
        processed.update({
            'start_timestamp': cls.safe_int(event_data.get('start_timestamp')),
            'end_timestamp': cls.safe_int(event_data.get('end_timestamp')),
            'ms': cls.safe_int(event_data.get('ms')),
            'wait_ms': cls.safe_int(event_data.get('wait_ms')),
            'overhead_ms': cls.safe_int(event_data.get('overhead_ms')),
            'lag_ms': cls.safe_int(event_data.get('lag_ms')),
            'total_ms': cls.safe_int(event_data.get('total_ms')),
        })
        
        # Version and handler info
        processed.update({
            'handler_version': cls.clean_string(event_data.get('handler_version'), 50),
            'version': cls.clean_string(event_data.get('version'), 50),
            'module_id': cls.clean_string(event_data.get('module_id'), 255),
            'package_version': cls.clean_string(event_data.get('package_version'), 50),
        })
        
        # Flow and step info
        processed.update({
            'step_id': cls.clean_string(event_data.get('step_id'), 50),
            'step_count': cls.safe_int(event_data.get('step_count')),
        })
        
        # Caps and limits
        processed.update({
            'cap_reached': cls.safe_bool(event_data.get('cap_reached')),
            'ping_limit_reached': cls.safe_bool(event_data.get('ping_limit_reached')),
        })
        
        # Pricing and revenue
        processed.update({
            'cost': cls.safe_decimal(event_data.get('cost')),
            'purchase_price': cls.safe_decimal(event_data.get('purchase_price')),
            'sale_price': cls.safe_decimal(event_data.get('sale_price')),
            'revenue': cls.safe_decimal(event_data.get('revenue')),
        })
        
        # JSON fields
        processed.update({
            'vars': event_data.get('vars'),
            'appended': event_data.get('appended'),
            'firehose': event_data.get('firehose'),
            'flow_ping_limits': event_data.get('flow_ping_limits'),
            'source_ping_limits': event_data.get('source_ping_limits'),
            'acceptance_criteria': event_data.get('acceptance_criteria'),
            'caps': event_data.get('caps'),
        })
        
        # HTTP request data
        request_data = event_data.get('request', {})
        if request_data:
            processed.update({
                'request_method': cls.clean_string(request_data.get('method'), 10),
                'request_uri': cls.clean_string(request_data.get('uri')),
                'request_version': cls.clean_string(request_data.get('version'), 10),
                'request_headers': request_data.get('headers'),
                'request_body': cls.clean_string(request_data.get('body')),
                'request_timestamp': cls.safe_int(request_data.get('timestamp')),
            })
        
        # HTTP response data
        response_data = event_data.get('response', {})
        if response_data:
            processed.update({
                'response_status': cls.safe_int(response_data.get('status')),
                'response_status_text': cls.clean_string(response_data.get('status_text'), 100),
                'response_version': cls.clean_string(response_data.get('version'), 10),
                'response_headers': response_data.get('headers'),
                'response_body': cls.clean_string(response_data.get('body')),
                'response_timestamp': cls.safe_int(response_data.get('timestamp')),
            })
        
        # Expiration
        expires_at = event_data.get('expires_at')
        if expires_at:
            try:
                from django.utils.dateparse import parse_datetime
                processed['expires_at'] = parse_datetime(expires_at)
            except Exception as e:
                logger.warning(f"Failed to parse expires_at: {expires_at} - {e}")
        
        return processed


class LeadProcessor(ActiveProspectProcessor):
    """Processor for ActiveProspect Lead data"""
    
    @classmethod
    def process_lead(cls, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw lead data into model fields"""
        logger.debug(f"Processing lead: {lead_data.get('lead_id', 'unknown')}")
        
        # Core identification
        processed = {
            'lead_id': cls.clean_string(lead_data.get('lead_id'), 50),
            'flow_id': cls.clean_string(lead_data.get('flow_id'), 50),
            'flow_name': cls.clean_string(lead_data.get('flow_name'), 255),
            'source_id': cls.clean_string(lead_data.get('source_id'), 50),
            'source_name': cls.clean_string(lead_data.get('source_name'), 255),
            'reference': cls.clean_string(lead_data.get('reference'), 255),
        }
        
        # Contact information
        processed.update({
            'first_name': cls.clean_string(lead_data.get('first_name'), 255),
            'last_name': cls.clean_string(lead_data.get('last_name'), 255),
            'email': cls.clean_string(lead_data.get('email')),
            'phone_1': cls.clean_string(lead_data.get('phone_1'), 20),
            'phone_2': cls.clean_string(lead_data.get('phone_2'), 20),
        })
        
        # Address information
        processed.update({
            'address_1': cls.clean_string(lead_data.get('address_1'), 255),
            'city': cls.clean_string(lead_data.get('city'), 100),
            'state': cls.clean_string(lead_data.get('state'), 50),
            'postal_code': cls.clean_string(lead_data.get('postal_code'), 20),
        })
        
        # Timestamps
        submission_timestamp = lead_data.get('submission_timestamp')
        if submission_timestamp:
            try:
                from django.utils.dateparse import parse_datetime
                processed['submission_timestamp'] = parse_datetime(submission_timestamp)
            except Exception as e:
                logger.warning(f"Failed to parse submission_timestamp: {submission_timestamp} - {e}")
        
        # Search metadata
        processed['highlight'] = lead_data.get('highlight')
        
        # Latest event reference
        latest_event = lead_data.get('latest_event', {})
        if latest_event:
            processed.update({
                'latest_event_id': cls.clean_string(latest_event.get('id'), 50),
                'latest_event_outcome': cls.clean_string(latest_event.get('outcome'), 50),
                'latest_event_data': latest_event,
            })
        
        return processed
