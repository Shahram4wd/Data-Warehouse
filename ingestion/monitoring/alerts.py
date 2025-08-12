"""
Enterprise Alert System for CRM Integrations
"""
import asyncio
import logging
import smtplib
import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from ingestion.base.performance import PerformanceMetrics
from ingestion.monitoring.dashboard import DashboardMetrics

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    """Alert types"""
    PERFORMANCE = "performance"
    ERROR_RATE = "error_rate"
    RESOURCE_USAGE = "resource_usage"
    SYNC_FAILURE = "sync_failure"
    DATA_QUALITY = "data_quality"
    SYSTEM_HEALTH = "system_health"

@dataclass
class Alert:
    """Alert data structure"""
    id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    source: str = "monitoring"
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert alert to dictionary"""
        return {
            'id': self.id,
            'type': self.alert_type.value,
            'severity': self.severity.value,
            'title': self.title,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'resolved': self.resolved,
            'resolution_time': self.resolution_time.isoformat() if self.resolution_time else None,
            'resolution_notes': self.resolution_notes
        }

@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    alert_type: AlertType
    severity: AlertSeverity
    condition: Callable[[Dict], bool]
    message_template: str
    cooldown_minutes: int = 60
    max_alerts_per_hour: int = 5
    enabled: bool = True
    
    def should_trigger(self, metrics: Dict) -> bool:
        """Check if alert should trigger based on metrics"""
        if not self.enabled:
            return False
        return self.condition(metrics)

class AlertManager:
    """Enterprise alert management system"""
    
    def __init__(self):
        self.rules = []
        self.active_alerts = {}
        self.alert_history = []
        self.notification_channels = []
        self.cooldown_tracker = {}
        self.alert_counter = {}
        self._alert_id_counter = 0
        self._alert_id_lock = threading.Lock()
        self.load_alert_rules()
        self.setup_notification_channels()
    
    def load_alert_rules(self):
        """Load alert rules configuration"""
        self.rules = [
            # Performance alerts
            AlertRule(
                name="low_success_rate",
                alert_type=AlertType.PERFORMANCE,
                severity=AlertSeverity.HIGH,
                condition=lambda m: m.get('success_rate_24h', 1.0) < 0.95,
                message_template="Success rate has dropped to {success_rate_24h:.1%}",
                cooldown_minutes=30
            ),
            
            AlertRule(
                name="slow_processing",
                alert_type=AlertType.PERFORMANCE,
                severity=AlertSeverity.MEDIUM,
                condition=lambda m: m.get('avg_processing_speed', 0) < 100,
                message_template="Processing speed is slow: {avg_processing_speed:.1f} records/minute",
                cooldown_minutes=60
            ),
            
            # Resource usage alerts
            AlertRule(
                name="high_memory_usage",
                alert_type=AlertType.RESOURCE_USAGE,
                severity=AlertSeverity.HIGH,
                condition=lambda m: m.get('avg_memory_usage', 0) > 500,
                message_template="High memory usage detected: {avg_memory_usage:.1f}MB",
                cooldown_minutes=15
            ),
            
            AlertRule(
                name="high_cpu_usage",
                alert_type=AlertType.RESOURCE_USAGE,
                severity=AlertSeverity.MEDIUM,
                condition=lambda m: m.get('avg_cpu_usage', 0) > 80,
                message_template="High CPU usage detected: {avg_cpu_usage:.1f}%",
                cooldown_minutes=30
            ),
            
            # Error rate alerts
            AlertRule(
                name="high_error_rate",
                alert_type=AlertType.ERROR_RATE,
                severity=AlertSeverity.HIGH,
                condition=lambda m: m.get('validation_error_rate', 0) > 0.05,
                message_template="High error rate: {validation_error_rate:.1%}",
                cooldown_minutes=30
            ),
            
            # Data quality alerts
            AlertRule(
                name="low_data_quality",
                alert_type=AlertType.DATA_QUALITY,
                severity=AlertSeverity.MEDIUM,
                condition=lambda m: m.get('data_quality_score', 1.0) < 0.9,
                message_template="Data quality score is low: {data_quality_score:.1%}",
                cooldown_minutes=60
            ),
            
            # System health alerts
            AlertRule(
                name="multiple_sync_failures",
                alert_type=AlertType.SYNC_FAILURE,
                severity=AlertSeverity.CRITICAL,
                condition=lambda m: m.get('failed_syncs_24h', 0) > 10,
                message_template="Multiple sync failures detected: {failed_syncs_24h} in last 24h",
                cooldown_minutes=120
            )
        ]
    
    def setup_notification_channels(self):
        """Setup notification channels"""
        self.notification_channels = [
            EmailNotificationChannel(),
            SlackNotificationChannel(),
            WebhookNotificationChannel(),
            DatabaseNotificationChannel()
        ]
    
    async def check_alerts(self, metrics: DashboardMetrics) -> List[Alert]:
        """Check all alert rules against current metrics"""
        triggered_alerts = []
        metrics_dict = metrics.__dict__
        
        for rule in self.rules:
            try:
                if rule.should_trigger(metrics_dict):
                    alert = await self.create_alert(rule, metrics_dict)
                    if alert:
                        triggered_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error checking alert rule {rule.name}: {e}")
        
        return triggered_alerts
    
    async def create_alert(self, rule: AlertRule, metrics: Dict) -> Optional[Alert]:
        """Create an alert if conditions are met with enhanced deduplication"""
        alert_key = f"{rule.name}_{rule.alert_type.value}"
        
        # Check cooldown
        if self.is_in_cooldown(alert_key, rule.cooldown_minutes):
            return None
        
        # Check rate limiting
        if self.exceeds_rate_limit(alert_key, rule.max_alerts_per_hour):
            return None
        
        # Create alert message
        alert_message = rule.message_template.format(**metrics)
        
        # Check for duplicate alert content in recent alerts
        if self.is_duplicate_alert_content(rule.name, alert_message):
            logger.debug(f"Skipping duplicate alert for {rule.name}: {alert_message}")
            return None
        
        # Create alert
        alert = Alert(
            id=self.generate_alert_id(),
            alert_type=rule.alert_type,
            severity=rule.severity,
            title=f"{rule.name.replace('_', ' ').title()} Alert",
            message=alert_message,
            details=metrics,
            timestamp=timezone.now(),
            source="alert_manager"
        )
        
        # Track alert
        self.active_alerts[alert.id] = alert
        self.alert_history.append(alert)
        self.update_cooldown(alert_key)
        self.update_rate_counter(alert_key)
        
        # Send notifications
        await self.send_notifications(alert)
        
        logger.warning(f"Alert triggered: {alert.title} - {alert.message}")
        return alert
    
    def is_in_cooldown(self, alert_key: str, cooldown_minutes: int) -> bool:
        """Check if alert is in cooldown period"""
        if alert_key not in self.cooldown_tracker:
            return False
        
        last_alert = self.cooldown_tracker[alert_key]
        cooldown_end = last_alert + timedelta(minutes=cooldown_minutes)
        return timezone.now() < cooldown_end
    
    def exceeds_rate_limit(self, alert_key: str, max_per_hour: int) -> bool:
        """Check if alert exceeds rate limit"""
        if alert_key not in self.alert_counter:
            return False
        
        hour_ago = timezone.now() - timedelta(hours=1)
        recent_alerts = [
            timestamp for timestamp in self.alert_counter[alert_key]
            if timestamp > hour_ago
        ]
        
        return len(recent_alerts) >= max_per_hour
    
    def update_cooldown(self, alert_key: str):
        """Update cooldown tracker"""
        self.cooldown_tracker[alert_key] = timezone.now()
    
    def update_rate_counter(self, alert_key: str):
        """Update rate counter"""
        if alert_key not in self.alert_counter:
            self.alert_counter[alert_key] = []
        
        self.alert_counter[alert_key].append(timezone.now())
        
        # Clean old entries
        hour_ago = timezone.now() - timedelta(hours=1)
        self.alert_counter[alert_key] = [
            timestamp for timestamp in self.alert_counter[alert_key]
            if timestamp > hour_ago
        ]
    
    def generate_alert_id(self) -> str:
        """Generate unique alert ID using timestamp, counter, and random component"""
        with self._alert_id_lock:
            self._alert_id_counter += 1
            timestamp_ms = int(timezone.now().timestamp() * 1000)  # Millisecond precision
            random_component = str(uuid.uuid4().hex)[:8]  # Short random string
            return f"alert_{timestamp_ms}_{self._alert_id_counter}_{random_component}"

    def is_duplicate_alert_content(self, rule_name: str, message: str, lookback_minutes: int = 10) -> bool:
        """Check if an alert with similar content was recently created"""
        cutoff_time = timezone.now() - timedelta(minutes=lookback_minutes)
        
        # Check recent alerts in history
        for alert in reversed(self.alert_history[-50:]):  # Check last 50 alerts
            if alert.timestamp < cutoff_time:
                break
                
            # Check if it's the same rule and same message
            if (alert.title.lower().replace(' ', '_') == f"{rule_name}_alert" and 
                alert.message == message):
                return True
                
        return False
    
    async def send_notifications(self, alert: Alert):
        """Send alert notifications through all channels"""
        for channel in self.notification_channels:
            try:
                await channel.send_notification(alert)
            except Exception as e:
                logger.error(f"Error sending notification via {channel.__class__.__name__}: {e}")
    
    async def resolve_alert(self, alert_id: str, resolution_notes: str = None):
        """Resolve an active alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolution_time = timezone.now()
            alert.resolution_notes = resolution_notes
            
            # Remove from active alerts
            del self.active_alerts[alert_id]
            
            # Send resolution notification
            await self.send_resolution_notification(alert)
            
            logger.info(f"Alert resolved: {alert.title}")
    
    async def send_resolution_notification(self, alert: Alert):
        """Send alert resolution notification"""
        resolution_alert = Alert(
            id=self.generate_alert_id(),
            alert_type=alert.alert_type,
            severity=AlertSeverity.LOW,
            title=f"RESOLVED: {alert.title}",
            message=f"Alert has been resolved: {alert.message}",
            details=alert.details,
            timestamp=timezone.now(),
            source="alert_manager",
            resolved=True
        )
        
        await self.send_notifications(resolution_alert)
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for specified hours"""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        return [
            alert for alert in self.alert_history
            if alert.timestamp > cutoff_time
        ]
    
    async def cleanup(self):
        """Cleanup alert manager resources"""
        try:
            # Clear active alerts
            self.active_alerts.clear()
            
            # Clear alert history (keep last 100 for reference)
            if len(self.alert_history) > 100:
                self.alert_history = self.alert_history[-100:]
            
            # Clear cooldown tracking
            self.cooldown_tracker.clear()
            
            # Reset alert counters
            self.alert_counter.clear()
            
            # Cleanup notification channels
            for channel in self.notification_channels:
                if hasattr(channel, 'cleanup'):
                    await channel.cleanup()
                    
            logger.info("Alert manager cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during alert manager cleanup: {e}")
    
    async def send_alert(self, alert_type: str, message: str, context: Dict = None, severity: str = 'info') -> None:
        """
        Send alert using enterprise alerting workflow
        
        This method provides compatibility with the legacy alert interface
        while using the enterprise alerting system internally.
        """
        try:
            # Map severity strings to AlertSeverity enum
            severity_mapping = {
                'info': AlertSeverity.LOW,
                'warning': AlertSeverity.MEDIUM,
                'error': AlertSeverity.HIGH,
                'critical': AlertSeverity.CRITICAL
            }
            
            # Map alert type strings to AlertType enum
            alert_type_mapping = {
                'sync_error': AlertType.SYNC_FAILURE,
                'sync_performance': AlertType.PERFORMANCE,
                'performance': AlertType.PERFORMANCE,
                'error_rate': AlertType.ERROR_RATE,
                'resource_usage': AlertType.RESOURCE_USAGE,
                'data_quality': AlertType.DATA_QUALITY,
                'system_health': AlertType.SYSTEM_HEALTH
            }
            
            # Get mapped values or defaults
            alert_severity = severity_mapping.get(severity, AlertSeverity.LOW)
            mapped_alert_type = alert_type_mapping.get(alert_type, AlertType.SYSTEM_HEALTH)
            
            # Create alert using enterprise system
            alert = Alert(
                id=self.generate_alert_id(),
                alert_type=mapped_alert_type,
                severity=alert_severity,
                title=f"{alert_type.replace('_', ' ').title()} Alert",
                message=message,
                details=context or {},
                timestamp=timezone.now(),
                source="compatibility_layer"
            )
            
            # Add to active alerts and history
            self.active_alerts[alert.id] = alert
            self.alert_history.append(alert)
            
            # Send notifications through enterprise channels
            await self.send_notifications(alert)
            
            logger.info(f"Alert sent via compatibility layer: {alert.title} - {alert.message}")
            
        except Exception as e:
            logger.error(f"Error in send_alert compatibility method: {e}")

class NotificationChannel:
    """Base class for notification channels"""
    
    async def send_notification(self, alert: Alert):
        """Send notification - to be implemented by subclasses"""
        raise NotImplementedError

class EmailNotificationChannel(NotificationChannel):
    """Email notification channel"""
    
    def __init__(self):
        self.smtp_settings = self.get_smtp_settings()
        self.recipients = self.get_recipients()
    
    def get_smtp_settings(self) -> Dict:
        """Get SMTP settings from Django configuration"""
        return {
            'host': getattr(settings, 'EMAIL_HOST', 'localhost'),
            'port': getattr(settings, 'EMAIL_PORT', 587),
            'username': getattr(settings, 'EMAIL_HOST_USER', ''),
            'password': getattr(settings, 'EMAIL_HOST_PASSWORD', ''),
            'use_tls': getattr(settings, 'EMAIL_USE_TLS', True),
            'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        }
    
    def get_recipients(self) -> List[str]:
        """Get alert recipients"""
        return getattr(settings, 'ALERT_EMAIL_RECIPIENTS', [])
    
    async def send_notification(self, alert: Alert):
        """Send email notification"""
        if not self.recipients:
            logger.warning("No email recipients configured for alerts")
            return
        
        subject = f"[{alert.severity.value.upper()}] {alert.title}"
        
        # Create HTML message
        html_message = self.create_html_message(alert)
        
        # Create text message
        text_message = self.create_text_message(alert)
        
        try:
            # Send email
            send_mail(
                subject=subject,
                message=text_message,
                html_message=html_message,
                from_email=self.smtp_settings['from_email'],
                recipient_list=self.recipients,
                fail_silently=False
            )
            
            logger.info(f"Email alert sent: {alert.title}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def create_html_message(self, alert: Alert) -> str:
        """Create HTML email message"""
        severity_colors = {
            AlertSeverity.LOW: "#28a745",
            AlertSeverity.MEDIUM: "#ffc107",
            AlertSeverity.HIGH: "#fd7e14",
            AlertSeverity.CRITICAL: "#dc3545"
        }
        
        color = severity_colors.get(alert.severity, "#6c757d")
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="border-left: 4px solid {color}; padding: 20px; margin: 20px 0;">
                <h2 style="color: {color}; margin: 0 0 10px 0;">{alert.title}</h2>
                <p><strong>Severity:</strong> {alert.severity.value.upper()}</p>
                <p><strong>Type:</strong> {alert.alert_type.value.replace('_', ' ').title()}</p>
                <p><strong>Time:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p><strong>Message:</strong> {alert.message}</p>
                
                <h3>Details:</h3>
                <ul>
                    {self.format_details_html(alert.details)}
                </ul>
            </div>
        </body>
        </html>
        """
    
    def create_text_message(self, alert: Alert) -> str:
        """Create text email message"""
        return f"""
        Alert: {alert.title}
        Severity: {alert.severity.value.upper()}
        Type: {alert.alert_type.value.replace('_', ' ').title()}
        Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
        
        Message: {alert.message}
        
        Details:
        {self.format_details_text(alert.details)}
        """
    
    def format_details_html(self, details: Dict) -> str:
        """Format details for HTML display"""
        items = []
        for key, value in details.items():
            if isinstance(value, (int, float)):
                if key.endswith('_rate') or key.endswith('_percent'):
                    value = f"{value:.1%}"
                elif key.endswith('_mb'):
                    value = f"{value:.1f} MB"
                elif key.endswith('_seconds'):
                    value = f"{value:.1f} seconds"
            items.append(f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>")
        return "".join(items)
    
    def format_details_text(self, details: Dict) -> str:
        """Format details for text display"""
        items = []
        for key, value in details.items():
            if isinstance(value, (int, float)):
                if key.endswith('_rate') or key.endswith('_percent'):
                    value = f"{value:.1%}"
                elif key.endswith('_mb'):
                    value = f"{value:.1f} MB"
                elif key.endswith('_seconds'):
                    value = f"{value:.1f} seconds"
            items.append(f"  {key.replace('_', ' ').title()}: {value}")
        return "\n".join(items)

class SlackNotificationChannel(NotificationChannel):
    """Slack notification channel"""
    
    def __init__(self):
        self.webhook_url = getattr(settings, 'SLACK_WEBHOOK_URL', None)
        self.channel = getattr(settings, 'SLACK_ALERT_CHANNEL', '#alerts')
    
    async def send_notification(self, alert: Alert):
        """Send Slack notification"""
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return
        
        # Create Slack message
        message = self.create_slack_message(alert)
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=message) as response:
                    if response.status == 200:
                        logger.info(f"Slack alert sent: {alert.title}")
                    else:
                        logger.error(f"Failed to send Slack alert: {response.status}")
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    def create_slack_message(self, alert: Alert) -> Dict:
        """Create Slack message format"""
        severity_colors = {
            AlertSeverity.LOW: "good",
            AlertSeverity.MEDIUM: "warning",
            AlertSeverity.HIGH: "danger",
            AlertSeverity.CRITICAL: "danger"
        }
        
        color = severity_colors.get(alert.severity, "good")
        
        return {
            "channel": self.channel,
            "username": "Data Warehouse Monitor",
            "icon_emoji": ":warning:",
            "attachments": [
                {
                    "color": color,
                    "title": alert.title,
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Type",
                            "value": alert.alert_type.value.replace('_', ' ').title(),
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
                            "short": True
                        }
                    ],
                    "footer": "Data Warehouse Monitoring",
                    "ts": int(alert.timestamp.timestamp())
                }
            ]
        }

class WebhookNotificationChannel(NotificationChannel):
    """Generic webhook notification channel"""
    
    def __init__(self):
        self.webhook_urls = getattr(settings, 'ALERT_WEBHOOK_URLS', [])
    
    async def send_notification(self, alert: Alert):
        """Send webhook notification"""
        if not self.webhook_urls:
            return
        
        payload = alert.to_dict()
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            for webhook_url in self.webhook_urls:
                try:
                    async with session.post(webhook_url, json=payload) as response:
                        if response.status == 200:
                            logger.info(f"Webhook alert sent to {webhook_url}")
                        else:
                            logger.error(f"Failed to send webhook alert to {webhook_url}: {response.status}")
                except Exception as e:
                    logger.error(f"Failed to send webhook alert to {webhook_url}: {e}")

class DatabaseNotificationChannel(NotificationChannel):
    """Database notification channel for storing alerts"""
    
    async def send_notification(self, alert: Alert):
        """Store alert in database with duplicate handling"""
        try:
            # Store in database using get_or_create to handle potential duplicates
            from ingestion.models.alerts import AlertModel
            from asgiref.sync import sync_to_async
            
            # Convert the get_or_create to async
            alert_obj, created = await sync_to_async(AlertModel.objects.get_or_create)(
                alert_id=alert.id,
                defaults={
                    'alert_type': alert.alert_type.value,
                    'severity': alert.severity.value,
                    'title': alert.title,
                    'message': alert.message,
                    'details': alert.details,
                    'timestamp': alert.timestamp,
                    'source': alert.source,
                    'resolved': alert.resolved
                }
            )
            
            if created:
                logger.info(f"Alert stored in database: {alert.title}")
            else:
                logger.info(f"Alert already exists in database: {alert.title}")
            
        except Exception as e:
            logger.error(f"Failed to store alert in database: {e}")

# Global alert manager instance
alert_manager = AlertManager()

# Alias for backward compatibility
AlertSystem = AlertManager

# Async task for periodic alert checking
async def periodic_alert_check():
    """Periodic alert checking task"""
    from ingestion.monitoring.dashboard import MonitoringDashboard
    
    dashboard = MonitoringDashboard()
    
    while True:
        try:
            # Get current metrics
            metrics = await dashboard.get_dashboard_metrics()
            
            # Check for alerts
            await alert_manager.check_alerts(metrics)
            
            # Sleep for check interval
            await asyncio.sleep(60)  # Check every minute
            
        except Exception as e:
            logger.error(f"Error in periodic alert check: {e}")
            await asyncio.sleep(60)

# Start periodic alert checking
def start_alert_monitoring():
    """Start the alert monitoring system"""
    asyncio.create_task(periodic_alert_check())
    logger.info("Alert monitoring started")
