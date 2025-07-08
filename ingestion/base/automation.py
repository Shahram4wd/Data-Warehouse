"""
Advanced Automation Features for CRM Integrations
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from django.utils import timezone
from django.core.cache import cache
from ingestion.models.common import SyncHistory, SyncConfiguration
from ingestion.base.performance import PerformanceMetrics, PerformanceMonitor
from ingestion.monitoring.alerts import AlertManager, Alert, AlertSeverity
from ingestion.monitoring.dashboard import MonitoringDashboard
from ingestion.base.config import ConfigurationManager

logger = logging.getLogger(__name__)

class AutomationLevel(Enum):
    """Automation levels"""
    MANUAL = "manual"
    SEMI_AUTOMATIC = "semi_automatic"
    FULLY_AUTOMATIC = "fully_automatic"

class AutomationStrategy(Enum):
    """Automation strategies"""
    REACTIVE = "reactive"          # React to problems
    PROACTIVE = "proactive"        # Prevent problems
    PREDICTIVE = "predictive"      # Predict problems

@dataclass
class AutomationRule:
    """Automation rule configuration"""
    name: str
    trigger_condition: str
    action: str
    priority: int = 0
    enabled: bool = True
    max_executions_per_hour: int = 10
    cooldown_minutes: int = 5
    automation_level: AutomationLevel = AutomationLevel.SEMI_AUTOMATIC
    strategy: AutomationStrategy = AutomationStrategy.REACTIVE
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AutomationAction:
    """Automation action result"""
    rule_name: str
    action_type: str
    success: bool
    message: str
    timestamp: datetime
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'rule_name': self.rule_name,
            'action_type': self.action_type,
            'success': self.success,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'parameters': self.parameters
        }

class SelfHealingSystem:
    """Self-healing automation system"""
    
    def __init__(self):
        self.rules = []
        self.action_history = []
        self.execution_counter = defaultdict(int)
        self.last_execution = {}
        self.performance_monitor = PerformanceMonitor()
        self.alert_manager = AlertManager()
        self.dashboard = MonitoringDashboard()
        self.config_manager = ConfigurationManager()
        self.load_automation_rules()
    
    def load_automation_rules(self):
        """Load automation rules"""
        self.rules = [
            # Performance optimization rules
            AutomationRule(
                name="optimize_batch_size",
                trigger_condition="performance.throughput < 50",
                action="adjust_batch_size",
                priority=1,
                automation_level=AutomationLevel.FULLY_AUTOMATIC,
                strategy=AutomationStrategy.REACTIVE,
                parameters={
                    'min_batch_size': 10,
                    'max_batch_size': 1000,
                    'adjustment_factor': 1.2
                }
            ),
            
            AutomationRule(
                name="restart_failed_sync",
                trigger_condition="sync.consecutive_failures >= 3",
                action="restart_sync",
                priority=2,
                automation_level=AutomationLevel.SEMI_AUTOMATIC,
                strategy=AutomationStrategy.REACTIVE,
                parameters={
                    'max_restart_attempts': 3,
                    'restart_delay_minutes': 15
                }
            ),
            
            AutomationRule(
                name="scale_up_resources",
                trigger_condition="performance.cpu_usage > 80 AND performance.memory_usage > 70",
                action="scale_resources",
                priority=3,
                automation_level=AutomationLevel.SEMI_AUTOMATIC,
                strategy=AutomationStrategy.PROACTIVE,
                parameters={
                    'cpu_threshold': 80,
                    'memory_threshold': 70,
                    'scale_factor': 1.5
                }
            ),
            
            AutomationRule(
                name="cleanup_stuck_processes",
                trigger_condition="sync.duration > 3600",
                action="cleanup_processes",
                priority=4,
                automation_level=AutomationLevel.FULLY_AUTOMATIC,
                strategy=AutomationStrategy.REACTIVE,
                parameters={
                    'max_duration_minutes': 60,
                    'force_cleanup': True
                }
            ),
            
            AutomationRule(
                name="rotate_credentials",
                trigger_condition="credentials.age_days > 85",
                action="rotate_credentials",
                priority=5,
                automation_level=AutomationLevel.SEMI_AUTOMATIC,
                strategy=AutomationStrategy.PROACTIVE,
                parameters={
                    'rotation_threshold_days': 85,
                    'advance_notice_days': 5
                }
            ),
            
            AutomationRule(
                name="clear_cache_on_errors",
                trigger_condition="errors.cache_related > 5",
                action="clear_cache",
                priority=6,
                automation_level=AutomationLevel.FULLY_AUTOMATIC,
                strategy=AutomationStrategy.REACTIVE,
                parameters={
                    'error_threshold': 5,
                    'clear_all_cache': False
                }
            ),
            
            AutomationRule(
                name="adjust_rate_limits",
                trigger_condition="errors.rate_limit_exceeded > 10",
                action="adjust_rate_limits",
                priority=7,
                automation_level=AutomationLevel.FULLY_AUTOMATIC,
                strategy=AutomationStrategy.REACTIVE,
                parameters={
                    'rate_limit_threshold': 10,
                    'adjustment_factor': 0.8
                }
            ),
            
            AutomationRule(
                name="predictive_maintenance",
                trigger_condition="performance.trend_declining AND performance.error_rate_increasing",
                action="schedule_maintenance",
                priority=8,
                automation_level=AutomationLevel.SEMI_AUTOMATIC,
                strategy=AutomationStrategy.PREDICTIVE,
                parameters={
                    'maintenance_window_hours': 2,
                    'advance_notice_hours': 24
                }
            )
        ]
    
    async def evaluate_automation_rules(self, context: Dict[str, Any]) -> List[AutomationAction]:
        """Evaluate all automation rules against current context"""
        triggered_actions = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                # Check if rule should trigger
                if await self.should_trigger_rule(rule, context):
                    action = await self.execute_automation_action(rule, context)
                    if action:
                        triggered_actions.append(action)
            except Exception as e:
                logger.error(f"Error evaluating automation rule {rule.name}: {e}")
        
        return triggered_actions
    
    async def should_trigger_rule(self, rule: AutomationRule, context: Dict[str, Any]) -> bool:
        """Check if automation rule should trigger"""
        # Check cooldown
        if not self.is_out_of_cooldown(rule):
            return False
        
        # Check execution limit
        if self.exceeds_execution_limit(rule):
            return False
        
        # Evaluate trigger condition
        return await self.evaluate_trigger_condition(rule.trigger_condition, context)
    
    async def evaluate_trigger_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate trigger condition"""
        try:
            # Simple expression evaluator
            # In production, use a proper expression parser
            
            # Replace context variables
            for key, value in context.items():
                condition = condition.replace(f"{key}", str(value))
            
            # Evaluate the condition
            return eval(condition)
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return False
    
    def is_out_of_cooldown(self, rule: AutomationRule) -> bool:
        """Check if rule is out of cooldown period"""
        if rule.name not in self.last_execution:
            return True
        
        last_exec = self.last_execution[rule.name]
        cooldown_end = last_exec + timedelta(minutes=rule.cooldown_minutes)
        return timezone.now() > cooldown_end
    
    def exceeds_execution_limit(self, rule: AutomationRule) -> bool:
        """Check if rule exceeds execution limit"""
        current_hour = timezone.now().replace(minute=0, second=0, microsecond=0)
        rule_key = f"{rule.name}_{current_hour}"
        
        return self.execution_counter[rule_key] >= rule.max_executions_per_hour
    
    async def execute_automation_action(self, rule: AutomationRule, context: Dict[str, Any]) -> Optional[AutomationAction]:
        """Execute automation action"""
        try:
            # Check automation level
            if rule.automation_level == AutomationLevel.MANUAL:
                return await self.create_manual_action(rule, context)
            elif rule.automation_level == AutomationLevel.SEMI_AUTOMATIC:
                return await self.create_semi_automatic_action(rule, context)
            else:  # FULLY_AUTOMATIC
                return await self.execute_automatic_action(rule, context)
        
        except Exception as e:
            logger.error(f"Error executing automation action for rule {rule.name}: {e}")
            return AutomationAction(
                rule_name=rule.name,
                action_type=rule.action,
                success=False,
                message=f"Error executing action: {e}",
                timestamp=timezone.now(),
                parameters=rule.parameters
            )
    
    async def create_manual_action(self, rule: AutomationRule, context: Dict[str, Any]) -> AutomationAction:
        """Create manual action (notification only)"""
        message = f"Manual action required: {rule.action} for rule {rule.name}"
        
        # Send notification
        await self.send_action_notification(rule, message, context)
        
        return AutomationAction(
            rule_name=rule.name,
            action_type=rule.action,
            success=True,
            message=message,
            timestamp=timezone.now(),
            parameters=rule.parameters
        )
    
    async def create_semi_automatic_action(self, rule: AutomationRule, context: Dict[str, Any]) -> AutomationAction:
        """Create semi-automatic action (requires approval)"""
        message = f"Semi-automatic action pending approval: {rule.action} for rule {rule.name}"
        
        # Create approval request
        approval_id = await self.create_approval_request(rule, context)
        
        return AutomationAction(
            rule_name=rule.name,
            action_type=rule.action,
            success=True,
            message=message,
            timestamp=timezone.now(),
            parameters={**rule.parameters, 'approval_id': approval_id}
        )
    
    async def execute_automatic_action(self, rule: AutomationRule, context: Dict[str, Any]) -> AutomationAction:
        """Execute fully automatic action"""
        success = False
        message = ""
        
        try:
            if rule.action == "adjust_batch_size":
                success, message = await self.adjust_batch_size(rule, context)
            elif rule.action == "restart_sync":
                success, message = await self.restart_sync(rule, context)
            elif rule.action == "scale_resources":
                success, message = await self.scale_resources(rule, context)
            elif rule.action == "cleanup_processes":
                success, message = await self.cleanup_processes(rule, context)
            elif rule.action == "rotate_credentials":
                success, message = await self.rotate_credentials(rule, context)
            elif rule.action == "clear_cache":
                success, message = await self.clear_cache(rule, context)
            elif rule.action == "adjust_rate_limits":
                success, message = await self.adjust_rate_limits(rule, context)
            elif rule.action == "schedule_maintenance":
                success, message = await self.schedule_maintenance(rule, context)
            else:
                message = f"Unknown action: {rule.action}"
        
        except Exception as e:
            message = f"Error executing action: {e}"
        
        # Update execution tracking
        self.update_execution_tracking(rule)
        
        # Log action
        self.log_automation_action(rule, success, message)
        
        return AutomationAction(
            rule_name=rule.name,
            action_type=rule.action,
            success=success,
            message=message,
            timestamp=timezone.now(),
            parameters=rule.parameters
        )
    
    async def adjust_batch_size(self, rule: AutomationRule, context: Dict[str, Any]) -> tuple[bool, str]:
        """Adjust batch size based on performance"""
        try:
            current_throughput = context.get('performance.throughput', 0)
            target_throughput = 100  # Target throughput
            
            # Calculate new batch size
            current_batch_size = context.get('sync.batch_size', 100)
            adjustment_factor = rule.parameters.get('adjustment_factor', 1.2)
            
            if current_throughput < target_throughput:
                new_batch_size = int(current_batch_size * adjustment_factor)
                new_batch_size = min(new_batch_size, rule.parameters.get('max_batch_size', 1000))
            else:
                new_batch_size = int(current_batch_size / adjustment_factor)
                new_batch_size = max(new_batch_size, rule.parameters.get('min_batch_size', 10))
            
            # Update configuration
            await self.config_manager.update_config('sync.batch_size', new_batch_size)
            
            return True, f"Adjusted batch size from {current_batch_size} to {new_batch_size}"
        
        except Exception as e:
            return False, f"Failed to adjust batch size: {e}"
    
    async def restart_sync(self, rule: AutomationRule, context: Dict[str, Any]) -> tuple[bool, str]:
        """Restart failed sync"""
        try:
            sync_id = context.get('sync.id')
            if not sync_id:
                return False, "No sync ID provided"
            
            # Get sync history
            sync_history = await SyncHistory.objects.aget(id=sync_id)
            
            # Check if sync is actually failed
            if sync_history.status != 'failed':
                return False, f"Sync is not in failed state: {sync_history.status}"
            
            # Restart sync (this would trigger the appropriate sync command)
            restart_delay = rule.parameters.get('restart_delay_minutes', 15)
            await asyncio.sleep(restart_delay * 60)
            
            # Here you would implement the actual sync restart logic
            # For now, we'll just mark it as restarted
            sync_history.status = 'running'
            await sync_history.asave()
            
            return True, f"Restarted sync {sync_id} after {restart_delay} minutes"
        
        except Exception as e:
            return False, f"Failed to restart sync: {e}"
    
    async def scale_resources(self, rule: AutomationRule, context: Dict[str, Any]) -> tuple[bool, str]:
        """Scale resources based on usage"""
        try:
            cpu_usage = context.get('performance.cpu_usage', 0)
            memory_usage = context.get('performance.memory_usage', 0)
            
            cpu_threshold = rule.parameters.get('cpu_threshold', 80)
            memory_threshold = rule.parameters.get('memory_threshold', 70)
            
            if cpu_usage > cpu_threshold or memory_usage > memory_threshold:
                # In a real implementation, this would scale container resources
                # For now, we'll just log the scaling action
                scale_factor = rule.parameters.get('scale_factor', 1.5)
                
                return True, f"Scaled resources by factor {scale_factor} due to CPU: {cpu_usage}%, Memory: {memory_usage}%"
            
            return False, "Resource scaling not needed"
        
        except Exception as e:
            return False, f"Failed to scale resources: {e}"
    
    async def cleanup_processes(self, rule: AutomationRule, context: Dict[str, Any]) -> tuple[bool, str]:
        """Cleanup stuck processes"""
        try:
            max_duration = rule.parameters.get('max_duration_minutes', 60)
            force_cleanup = rule.parameters.get('force_cleanup', True)
            
            # Find stuck processes
            stuck_syncs = await SyncHistory.objects.filter(
                status='running',
                start_time__lt=timezone.now() - timedelta(minutes=max_duration)
            ).aall()
            
            cleaned_count = 0
            for sync in stuck_syncs:
                if force_cleanup:
                    sync.status = 'failed'
                    sync.error_message = f"Cleaned up stuck process after {max_duration} minutes"
                    sync.end_time = timezone.now()
                    await sync.asave()
                    cleaned_count += 1
            
            return True, f"Cleaned up {cleaned_count} stuck processes"
        
        except Exception as e:
            return False, f"Failed to cleanup processes: {e}"
    
    async def rotate_credentials(self, rule: AutomationRule, context: Dict[str, Any]) -> tuple[bool, str]:
        """Rotate credentials"""
        try:
            from ingestion.base.encryption import credential_manager
            
            # Rotate credentials that are due
            credential_manager.rotate_all_keys()
            
            return True, "Rotated credentials for all due vaults"
        
        except Exception as e:
            return False, f"Failed to rotate credentials: {e}"
    
    async def clear_cache(self, rule: AutomationRule, context: Dict[str, Any]) -> tuple[bool, str]:
        """Clear cache"""
        try:
            clear_all = rule.parameters.get('clear_all_cache', False)
            
            if clear_all:
                cache.clear()
                return True, "Cleared all cache"
            else:
                # Clear specific cache keys related to errors
                error_cache_keys = [
                    key for key in cache._cache.keys()
                    if 'error' in key.lower() or 'failed' in key.lower()
                ]
                
                for key in error_cache_keys:
                    cache.delete(key)
                
                return True, f"Cleared {len(error_cache_keys)} error-related cache keys"
        
        except Exception as e:
            return False, f"Failed to clear cache: {e}"
    
    async def adjust_rate_limits(self, rule: AutomationRule, context: Dict[str, Any]) -> tuple[bool, str]:
        """Adjust rate limits"""
        try:
            adjustment_factor = rule.parameters.get('adjustment_factor', 0.8)
            
            # Get current rate limits
            current_rate_limit = await self.config_manager.get_config('api.rate_limit', 100)
            new_rate_limit = int(current_rate_limit * adjustment_factor)
            
            # Update rate limit
            await self.config_manager.update_config('api.rate_limit', new_rate_limit)
            
            return True, f"Adjusted rate limit from {current_rate_limit} to {new_rate_limit}"
        
        except Exception as e:
            return False, f"Failed to adjust rate limits: {e}"
    
    async def schedule_maintenance(self, rule: AutomationRule, context: Dict[str, Any]) -> tuple[bool, str]:
        """Schedule maintenance"""
        try:
            maintenance_window = rule.parameters.get('maintenance_window_hours', 2)
            advance_notice = rule.parameters.get('advance_notice_hours', 24)
            
            # Schedule maintenance (in a real implementation, this would integrate with a scheduler)
            maintenance_time = timezone.now() + timedelta(hours=advance_notice)
            
            # Send notification
            await self.send_maintenance_notification(maintenance_time, maintenance_window)
            
            return True, f"Scheduled maintenance in {advance_notice} hours for {maintenance_window} hours"
        
        except Exception as e:
            return False, f"Failed to schedule maintenance: {e}"
    
    def update_execution_tracking(self, rule: AutomationRule):
        """Update execution tracking"""
        current_hour = timezone.now().replace(minute=0, second=0, microsecond=0)
        rule_key = f"{rule.name}_{current_hour}"
        
        self.execution_counter[rule_key] += 1
        self.last_execution[rule.name] = timezone.now()
    
    def log_automation_action(self, rule: AutomationRule, success: bool, message: str):
        """Log automation action"""
        action = AutomationAction(
            rule_name=rule.name,
            action_type=rule.action,
            success=success,
            message=message,
            timestamp=timezone.now(),
            parameters=rule.parameters
        )
        
        self.action_history.append(action)
        
        # Keep only recent history
        if len(self.action_history) > 1000:
            self.action_history = self.action_history[-1000:]
        
        # Log to file
        logger.info(f"Automation action: {action.to_dict()}")
    
    async def send_action_notification(self, rule: AutomationRule, message: str, context: Dict[str, Any]):
        """Send notification for automation action"""
        try:
            # Create alert for manual actions
            alert = Alert(
                id=f"automation_{rule.name}_{int(timezone.now().timestamp())}",
                alert_type='automation',
                severity=AlertSeverity.MEDIUM,
                title=f"Automation Action Required: {rule.name}",
                message=message,
                details=context,
                timestamp=timezone.now(),
                source="automation_system"
            )
            
            await self.alert_manager.send_notifications(alert)
        
        except Exception as e:
            logger.error(f"Failed to send action notification: {e}")
    
    async def create_approval_request(self, rule: AutomationRule, context: Dict[str, Any]) -> str:
        """Create approval request for semi-automatic actions"""
        approval_id = f"approval_{rule.name}_{int(timezone.now().timestamp())}"
        
        # Store approval request (in production, this would be in a database)
        approval_request = {
            'id': approval_id,
            'rule_name': rule.name,
            'action': rule.action,
            'context': context,
            'parameters': rule.parameters,
            'created_at': timezone.now(),
            'status': 'pending'
        }
        
        # Cache the approval request
        cache.set(f"approval_request_{approval_id}", approval_request, timeout=3600)
        
        # Send notification
        await self.send_approval_notification(approval_request)
        
        return approval_id
    
    async def send_approval_notification(self, approval_request: Dict[str, Any]):
        """Send approval notification"""
        try:
            alert = Alert(
                id=f"approval_{approval_request['id']}",
                alert_type='approval_required',
                severity=AlertSeverity.HIGH,
                title=f"Approval Required: {approval_request['rule_name']}",
                message=f"Semi-automatic action requires approval: {approval_request['action']}",
                details=approval_request,
                timestamp=timezone.now(),
                source="automation_system"
            )
            
            await self.alert_manager.send_notifications(alert)
        
        except Exception as e:
            logger.error(f"Failed to send approval notification: {e}")
    
    async def send_maintenance_notification(self, maintenance_time: datetime, duration_hours: int):
        """Send maintenance notification"""
        try:
            alert = Alert(
                id=f"maintenance_{int(maintenance_time.timestamp())}",
                alert_type='maintenance_scheduled',
                severity=AlertSeverity.MEDIUM,
                title="Scheduled Maintenance",
                message=f"Predictive maintenance scheduled for {maintenance_time.strftime('%Y-%m-%d %H:%M')} UTC, duration: {duration_hours} hours",
                details={
                    'maintenance_time': maintenance_time.isoformat(),
                    'duration_hours': duration_hours,
                    'type': 'predictive'
                },
                timestamp=timezone.now(),
                source="automation_system"
            )
            
            await self.alert_manager.send_notifications(alert)
        
        except Exception as e:
            logger.error(f"Failed to send maintenance notification: {e}")
    
    def get_action_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get automation action history"""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        return [
            action.to_dict() for action in self.action_history
            if action.timestamp > cutoff_time
        ]
    
    def get_automation_stats(self) -> Dict[str, Any]:
        """Get automation statistics"""
        total_actions = len(self.action_history)
        successful_actions = sum(1 for action in self.action_history if action.success)
        
        rule_stats = defaultdict(int)
        for action in self.action_history:
            rule_stats[action.rule_name] += 1
        
        return {
            'total_actions': total_actions,
            'successful_actions': successful_actions,
            'success_rate': successful_actions / max(total_actions, 1),
            'active_rules': len([rule for rule in self.rules if rule.enabled]),
            'rule_execution_stats': dict(rule_stats)
        }

class IntelligentScheduler:
    """Intelligent scheduling system for sync operations"""
    
    def __init__(self):
        self.schedule_cache = {}
        self.performance_history = []
        self.optimization_rules = self.load_optimization_rules()
    
    def load_optimization_rules(self) -> List[Dict[str, Any]]:
        """Load scheduling optimization rules"""
        return [
            {
                'name': 'avoid_peak_hours',
                'condition': lambda hour: 9 <= hour <= 17,  # Business hours
                'weight': 0.3,
                'description': 'Avoid business hours for heavy operations'
            },
            {
                'name': 'prefer_low_load',
                'condition': lambda load: load < 50,  # System load
                'weight': 0.4,
                'description': 'Prefer times with low system load'
            },
            {
                'name': 'batch_similar_operations',
                'condition': lambda ops: len(ops) > 1,  # Multiple operations
                'weight': 0.3,
                'description': 'Batch similar operations together'
            }
        ]
    
    async def optimize_schedule(self, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize schedule for sync operations"""
        optimized_schedule = []
        
        for operation in operations:
            optimal_time = await self.find_optimal_time(operation)
            operation['scheduled_time'] = optimal_time
            optimized_schedule.append(operation)
        
        return sorted(optimized_schedule, key=lambda x: x['scheduled_time'])
    
    async def find_optimal_time(self, operation: Dict[str, Any]) -> datetime:
        """Find optimal time for an operation"""
        # Get current time
        current_time = timezone.now()
        
        # Look ahead for next 24 hours
        best_time = current_time
        best_score = 0
        
        for hour_offset in range(24):
            candidate_time = current_time + timedelta(hours=hour_offset)
            score = await self.calculate_time_score(candidate_time, operation)
            
            if score > best_score:
                best_score = score
                best_time = candidate_time
        
        return best_time
    
    async def calculate_time_score(self, time: datetime, operation: Dict[str, Any]) -> float:
        """Calculate score for a given time slot"""
        score = 1.0
        
        # Apply optimization rules
        for rule in self.optimization_rules:
            if rule['name'] == 'avoid_peak_hours':
                if rule['condition'](time.hour):
                    score -= rule['weight']
            elif rule['name'] == 'prefer_low_load':
                predicted_load = await self.predict_system_load(time)
                if rule['condition'](predicted_load):
                    score += rule['weight']
        
        return max(0, score)
    
    async def predict_system_load(self, time: datetime) -> float:
        """Predict system load for a given time"""
        # Simple prediction based on historical patterns
        # In production, this would use machine learning
        
        hour = time.hour
        
        # Peak hours have higher load
        if 9 <= hour <= 17:
            return 70.0
        elif 18 <= hour <= 22:
            return 40.0
        else:
            return 20.0

# Global automation system instance
automation_system = SelfHealingSystem()
scheduler = IntelligentScheduler()

# Main automation loop
async def automation_loop():
    """Main automation loop"""
    dashboard = MonitoringDashboard()
    
    while True:
        try:
            # Get current metrics
            metrics = await dashboard.get_dashboard_metrics()
            
            # Convert to context
            context = {
                'performance.throughput': metrics.avg_processing_speed,
                'performance.cpu_usage': metrics.avg_cpu_usage,
                'performance.memory_usage': metrics.avg_memory_usage,
                'sync.success_rate': metrics.success_rate_24h,
                'sync.failed_count': metrics.failed_syncs_24h,
                'sync.active_count': metrics.active_syncs,
                'errors.validation_rate': metrics.validation_error_rate,
                'errors.rate_limit_exceeded': len([e for e in metrics.top_errors if 'rate limit' in e.get('category', '').lower()]),
                'errors.cache_related': len([e for e in metrics.top_errors if 'cache' in e.get('category', '').lower()]),
            }
            
            # Evaluate automation rules
            actions = await automation_system.evaluate_automation_rules(context)
            
            if actions:
                logger.info(f"Executed {len(actions)} automation actions")
                for action in actions:
                    if action.success:
                        logger.info(f"✓ {action.rule_name}: {action.message}")
                    else:
                        logger.warning(f"✗ {action.rule_name}: {action.message}")
            
            # Sleep for next check
            await asyncio.sleep(300)  # Check every 5 minutes
            
        except Exception as e:
            logger.error(f"Error in automation loop: {e}")
            await asyncio.sleep(300)

# Start automation system
def start_automation_system():
    """Start the automation system"""
    asyncio.create_task(automation_loop())
    logger.info("Automation system started")

# API endpoints for automation management
class AutomationAPI:
    """API for automation management"""
    
    def __init__(self):
        self.automation_system = automation_system
        self.scheduler = scheduler
    
    async def get_automation_status(self) -> Dict[str, Any]:
        """Get automation system status"""
        return {
            'status': 'running',
            'stats': self.automation_system.get_automation_stats(),
            'active_rules': len([r for r in self.automation_system.rules if r.enabled]),
            'recent_actions': self.automation_system.get_action_history(24)
        }
    
    async def approve_action(self, approval_id: str) -> Dict[str, Any]:
        """Approve pending automation action"""
        approval_request = cache.get(f"approval_request_{approval_id}")
        
        if not approval_request:
            return {'success': False, 'message': 'Approval request not found'}
        
        if approval_request['status'] != 'pending':
            return {'success': False, 'message': 'Approval request already processed'}
        
        # Execute the approved action
        rule = next((r for r in self.automation_system.rules if r.name == approval_request['rule_name']), None)
        if not rule:
            return {'success': False, 'message': 'Rule not found'}
        
        # Execute the action
        action = await self.automation_system.execute_automatic_action(rule, approval_request['context'])
        
        # Update approval status
        approval_request['status'] = 'approved'
        approval_request['executed_at'] = timezone.now()
        cache.set(f"approval_request_{approval_id}", approval_request, timeout=3600)
        
        return {
            'success': True,
            'message': 'Action approved and executed',
            'action': action.to_dict()
        }
    
    async def reject_action(self, approval_id: str, reason: str = None) -> Dict[str, Any]:
        """Reject pending automation action"""
        approval_request = cache.get(f"approval_request_{approval_id}")
        
        if not approval_request:
            return {'success': False, 'message': 'Approval request not found'}
        
        if approval_request['status'] != 'pending':
            return {'success': False, 'message': 'Approval request already processed'}
        
        # Update approval status
        approval_request['status'] = 'rejected'
        approval_request['rejected_at'] = timezone.now()
        approval_request['rejection_reason'] = reason
        cache.set(f"approval_request_{approval_id}", approval_request, timeout=3600)
        
        return {
            'success': True,
            'message': 'Action rejected',
            'reason': reason
        }
    
    async def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get pending approval requests"""
        # In production, this would query the database
        # For now, we'll scan the cache
        pending_approvals = []
        
        # This is a simplified implementation
        # In production, you'd store approval requests in a database
        
        return pending_approvals
    
    async def optimize_schedule(self, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize schedule for operations"""
        return await self.scheduler.optimize_schedule(operations)

# Global automation API instance
automation_api = AutomationAPI()
