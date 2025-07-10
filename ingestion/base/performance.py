"""
Performance monitoring for sync operations
"""
import time
import psutil
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from contextlib import contextmanager
from functools import wraps
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    memory_usage_mb: float = 0
    cpu_percent: float = 0
    records_processed: int = 0
    errors_count: int = 0
    success_rate: float = 0
    throughput: float = 0  # records per second
    additional_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self, records_processed: int = None, errors_count: int = None):
        """Mark operation as finished and calculate metrics"""
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        
        if records_processed is not None:
            self.records_processed = records_processed
        if errors_count is not None:
            self.errors_count = errors_count
        
        # Calculate success rate
        if self.records_processed > 0:
            self.success_rate = (self.records_processed - self.errors_count) / self.records_processed
        
        # Calculate throughput
        if self.duration > 0:
            self.throughput = self.records_processed / self.duration
        
        # Get current system metrics
        self.memory_usage_mb = psutil.Process().memory_info().rss / 1024 / 1024
        self.cpu_percent = psutil.Process().cpu_percent()

class PerformanceMonitor:
    """Performance monitoring system"""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.metrics: List[PerformanceMetrics] = []
        self.active_operations: Dict[str, PerformanceMetrics] = {}
        self.aggregated_metrics: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.logger = logging.getLogger(__name__)
    
    def start_operation(self, operation_name: str) -> str:
        """Start monitoring an operation"""
        operation_id = f"{operation_name}_{int(time.time())}"
        
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            start_time=datetime.now()
        )
        
        self.active_operations[operation_id] = metrics
        self.logger.debug(f"Started monitoring operation: {operation_name}")
        
        return operation_id
    
    def finish_operation(
        self,
        operation_id: str,
        records_processed: int = 0,
        errors_count: int = 0,
        additional_metrics: Dict[str, Any] = None
    ) -> PerformanceMetrics:
        """Finish monitoring an operation"""
        if operation_id not in self.active_operations:
            self.logger.warning(f"Operation {operation_id} not found in active operations")
            return None
        
        metrics = self.active_operations.pop(operation_id)
        metrics.finish(records_processed, errors_count)
        
        if additional_metrics:
            metrics.additional_metrics.update(additional_metrics)
        
        self.metrics.append(metrics)
        self._update_aggregated_metrics(metrics)
        
        self.logger.info(
            f"Operation {metrics.operation_name} completed: "
            f"{metrics.records_processed} records in {metrics.duration:.2f}s "
            f"({metrics.throughput:.2f} records/s, {metrics.success_rate:.2%} success rate)"
        )
        
        return metrics
    
    def get_system_metrics(self) -> Dict[str, float]:
        """Get current system metrics"""
        return {
            'memory_usage_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'memory_percent': psutil.Process().memory_percent(),
            'cpu_percent': psutil.Process().cpu_percent(),
            'disk_usage_percent': psutil.disk_usage('/').percent,
            'available_memory_mb': psutil.virtual_memory().available / 1024 / 1024,
        }
    
    def check_memory_threshold(self, threshold: float = 0.8) -> bool:
        """Check if memory usage exceeds threshold"""
        memory_percent = psutil.Process().memory_percent()
        return memory_percent > threshold * 100
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get statistics for a specific operation"""
        operation_metrics = [m for m in self.metrics if m.operation_name == operation_name]
        
        if not operation_metrics:
            return {}
        
        durations = [m.duration for m in operation_metrics if m.duration]
        throughputs = [m.throughput for m in operation_metrics if m.throughput]
        success_rates = [m.success_rate for m in operation_metrics]
        
        return {
            'count': len(operation_metrics),
            'avg_duration': sum(durations) / len(durations) if durations else 0,
            'min_duration': min(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
            'avg_throughput': sum(throughputs) / len(throughputs) if throughputs else 0,
            'avg_success_rate': sum(success_rates) / len(success_rates) if success_rates else 0,
            'total_records': sum(m.records_processed for m in operation_metrics),
            'total_errors': sum(m.errors_count for m in operation_metrics),
        }
    
    def get_summary_report(self) -> Dict[str, Any]:
        """Get a summary report of all operations"""
        if not self.metrics:
            return {'message': 'No operations recorded'}
        
        operations = set(m.operation_name for m in self.metrics)
        report = {
            'total_operations': len(self.metrics),
            'operation_types': len(operations),
            'time_range': {
                'start': min(m.start_time for m in self.metrics),
                'end': max(m.end_time for m in self.metrics if m.end_time),
            },
            'operations': {}
        }
        
        for operation in operations:
            report['operations'][operation] = self.get_operation_stats(operation)
        
        return report
    
    def _update_aggregated_metrics(self, metrics: PerformanceMetrics):
        """Update aggregated metrics"""
        op_name = metrics.operation_name
        
        if op_name not in self.aggregated_metrics:
            self.aggregated_metrics[op_name] = {
                'total_records': 0,
                'total_errors': 0,
                'total_duration': 0,
                'operation_count': 0,
            }
        
        agg = self.aggregated_metrics[op_name]
        agg['total_records'] += metrics.records_processed
        agg['total_errors'] += metrics.errors_count
        agg['total_duration'] += metrics.duration or 0
        agg['operation_count'] += 1
        
        # Calculate averages
        agg['avg_duration'] = agg['total_duration'] / agg['operation_count']
        agg['avg_throughput'] = agg['total_records'] / agg['total_duration'] if agg['total_duration'] > 0 else 0
        agg['success_rate'] = (agg['total_records'] - agg['total_errors']) / agg['total_records'] if agg['total_records'] > 0 else 0
    
    @contextmanager
    def monitor_operation(self, operation_name: str, **kwargs):
        """Context manager for monitoring operations"""
        operation_id = self.start_operation(operation_name)
        
        try:
            yield operation_id
        except Exception as e:
            kwargs['errors_count'] = kwargs.get('errors_count', 0) + 1
            raise
        finally:
            self.finish_operation(operation_id, **kwargs)
    
    def clear_metrics(self):
        """Clear all stored metrics"""
        self.metrics.clear()
        self.aggregated_metrics.clear()
        self.active_operations.clear()
    
    def cleanup(self):
        """Cleanup performance monitor resources and clear all data"""
        try:
            # Clear all metrics and active operations
            self.clear_metrics()
            
            # Cancel any active operations with cleanup notification
            for operation_id, metrics in list(self.active_operations.items()):
                self.logger.info(f"Cleaning up active operation: {metrics.operation_name}")
                metrics.finish(records_processed=0, errors_count=0)
                self.metrics.append(metrics)
            
            # Clear active operations again after processing
            self.active_operations.clear()
            
            # Reset aggregated metrics
            self.aggregated_metrics.clear()
            
            self.logger.info(f"Performance monitor '{self.name}' cleaned up successfully")
            
        except Exception as e:
            self.logger.error(f"Error during performance monitor cleanup: {e}")
            # Ensure we clear what we can even if there's an error
            self.metrics.clear()
            self.active_operations.clear()
            self.aggregated_metrics.clear()
            raise

# Global performance monitor instance
performance_monitor = PerformanceMonitor("sync_operations")

# Decorators for performance monitoring
def monitor_performance(operation_name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with performance_monitor.monitor_operation(op_name) as operation_id:
                result = func(*args, **kwargs)
                
                # Try to extract metrics from result if it's a tuple
                if isinstance(result, tuple) and len(result) == 2:
                    actual_result, metrics = result
                    if isinstance(metrics, dict):
                        performance_monitor.finish_operation(
                            operation_id,
                            records_processed=metrics.get('records_processed', 0),
                            errors_count=metrics.get('errors_count', 0),
                            additional_metrics=metrics
                        )
                        return actual_result
                
                return result
        
        return wrapper
    return decorator

def track_memory_usage(func: Callable) -> Callable:
    """Decorator to track memory usage"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import tracemalloc
        tracemalloc.start()
        
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            result = func(*args, **kwargs)
            
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_diff = end_memory - start_memory
            
            logger.info(f"Memory usage for {func.__name__}: "
                       f"{memory_diff:.2f} MB ({start_memory:.2f} -> {end_memory:.2f} MB)")
            
            return result
        finally:
            tracemalloc.stop()
    
    return wrapper

def check_resource_limits(memory_threshold: float = 0.8, cpu_threshold: float = 80.0):
    """Decorator to check resource limits before execution"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check memory usage
            memory_percent = psutil.Process().memory_percent()
            if memory_percent > memory_threshold * 100:
                logger.warning(f"High memory usage detected: {memory_percent:.1f}%")
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > cpu_threshold:
                logger.warning(f"High CPU usage detected: {cpu_percent:.1f}%")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
