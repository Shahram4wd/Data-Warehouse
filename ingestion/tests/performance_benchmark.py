"""
Performance benchmarking suite for HubSpot sync operations
Measures and compares performance metrics between old and new implementations
"""
import time
import psutil
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from statistics import mean, median, stdev
from django.core.management import call_command
from django.utils import timezone
from io import StringIO

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for a single test run"""
    command: str
    duration: float
    memory_start: float
    memory_peak: float
    memory_end: float
    memory_delta: float
    records_processed: int
    records_per_second: float
    cpu_percent: float
    success: bool
    error_message: Optional[str] = None

@dataclass
class BenchmarkResult:
    """Results of a performance benchmark"""
    test_name: str
    old_metrics: List[PerformanceMetrics]
    new_metrics: List[PerformanceMetrics]
    comparison: Dict[str, Any]
    recommendations: List[str]

class PerformanceBenchmark:
    """Performance benchmarking framework for HubSpot sync operations"""
    
    def __init__(self, iterations: int = 3, warmup_runs: int = 1):
        """
        Initialize benchmark suite
        
        Args:
            iterations: Number of test iterations to run
            warmup_runs: Number of warmup runs before measuring (default: 1)
        """
        self.iterations = iterations
        self.warmup_runs = warmup_runs
        self.process = psutil.Process(os.getpid())
    
    def measure_command_performance(self, command: str, *args, **kwargs) -> PerformanceMetrics:
        """Measure performance of a single command execution"""
        # Record initial state
        memory_start = self.process.memory_info().rss / 1024 / 1024  # MB
        cpu_start = self.process.cpu_percent()
        
        # Start timing
        start_time = time.time()
        stdout = StringIO()
        
        # Track peak memory usage
        memory_peak = memory_start
        
        def monitor_memory():
            nonlocal memory_peak
            while True:
                try:
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    memory_peak = max(memory_peak, current_memory)
                    time.sleep(0.1)  # Check every 100ms
                except:
                    break
        
        # Start memory monitoring in background
        import threading
        monitor_thread = threading.Thread(target=monitor_memory)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        try:
            # Execute command
            call_command(command, *args, stdout=stdout, **kwargs)
            success = True
            error_message = None
        except Exception as e:
            success = False
            error_message = str(e)
        
        # Stop timing
        end_time = time.time()
        duration = end_time - start_time
        
        # Record final state
        memory_end = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_delta = memory_end - memory_start
        cpu_end = self.process.cpu_percent()
        cpu_percent = (cpu_start + cpu_end) / 2  # Average
        
        # Parse output for record count (if available)
        output = stdout.getvalue()
        records_processed = self._extract_record_count(output)
        records_per_second = records_processed / duration if duration > 0 else 0
        
        return PerformanceMetrics(
            command=command,
            duration=duration,
            memory_start=memory_start,
            memory_peak=memory_peak,
            memory_end=memory_end,
            memory_delta=memory_delta,
            records_processed=records_processed,
            records_per_second=records_per_second,
            cpu_percent=cpu_percent,
            success=success,
            error_message=error_message
        )
    
    def benchmark_contact_sync(self, limit: int = 500) -> BenchmarkResult:
        """Benchmark contact sync performance"""
        logger.info(f"Benchmarking contact sync performance (limit: {limit})")
        
        # Warmup runs
        for i in range(self.warmup_runs):
            logger.info(f"Warmup run {i+1}/{self.warmup_runs}")
            try:
                self.measure_command_performance(
                    'sync_hubspot_contacts_new',
                    dry_run=True,
                    batch_size=50
                )
            except:
                pass  # Ignore warmup errors
        
        old_metrics = []
        new_metrics = []
        
        # Run old command iterations
        for i in range(self.iterations):
            logger.info(f"Testing old contact sync - iteration {i+1}/{self.iterations}")
            try:
                metrics = self.measure_command_performance(
                    'sync_hubspot_contacts',
                    dry_run=True,
                    pages=1
                )
                old_metrics.append(metrics)
            except Exception as e:
                logger.error(f"Old command failed: {e}")
        
        # Run new command iterations
        for i in range(self.iterations):
            logger.info(f"Testing new contact sync - iteration {i+1}/{self.iterations}")
            try:
                metrics = self.measure_command_performance(
                    'sync_hubspot_contacts_new',
                    dry_run=True,
                    batch_size=limit
                )
                new_metrics.append(metrics)
            except Exception as e:
                logger.error(f"New command failed: {e}")
        
        # Generate comparison
        comparison = self._compare_metrics(old_metrics, new_metrics)
        recommendations = self._generate_performance_recommendations(comparison)
        
        return BenchmarkResult(
            test_name='contact_sync',
            old_metrics=old_metrics,
            new_metrics=new_metrics,
            comparison=comparison,
            recommendations=recommendations
        )
    
    def benchmark_appointment_sync(self, limit: int = 500) -> BenchmarkResult:
        """Benchmark appointment sync performance"""
        logger.info(f"Benchmarking appointment sync performance (limit: {limit})")
        
        # Warmup runs
        for i in range(self.warmup_runs):
            logger.info(f"Warmup run {i+1}/{self.warmup_runs}")
            try:
                self.measure_command_performance(
                    'sync_hubspot_appointments_new',
                    dry_run=True,
                    batch_size=50
                )
            except:
                pass
        
        old_metrics = []
        new_metrics = []
        
        # Run old command iterations
        for i in range(self.iterations):
            logger.info(f"Testing old appointment sync - iteration {i+1}/{self.iterations}")
            try:
                metrics = self.measure_command_performance(
                    'sync_hubspot_appointments',
                    dry_run=True,
                    pages=1
                )
                old_metrics.append(metrics)
            except Exception as e:
                logger.error(f"Old command failed: {e}")
        
        # Run new command iterations
        for i in range(self.iterations):
            logger.info(f"Testing new appointment sync - iteration {i+1}/{self.iterations}")
            try:
                metrics = self.measure_command_performance(
                    'sync_hubspot_appointments_new',
                    dry_run=True,
                    batch_size=limit
                )
                new_metrics.append(metrics)
            except Exception as e:
                logger.error(f"New command failed: {e}")
        
        # Generate comparison
        comparison = self._compare_metrics(old_metrics, new_metrics)
        recommendations = self._generate_performance_recommendations(comparison)
        
        return BenchmarkResult(
            test_name='appointment_sync',
            old_metrics=old_metrics,
            new_metrics=new_metrics,
            comparison=comparison,
            recommendations=recommendations
        )
    
    def benchmark_all_syncs(self) -> List[BenchmarkResult]:
        """Benchmark all sync operations"""
        logger.info("Starting comprehensive performance benchmarking")
        
        benchmarks = []
        
        # Define benchmarks to run
        benchmark_tests = [
            ('contacts', self.benchmark_contact_sync),
            ('appointments', self.benchmark_appointment_sync),
        ]
        
        for test_name, benchmark_func in benchmark_tests:
            try:
                logger.info(f"Running {test_name} benchmark...")
                result = benchmark_func()
                benchmarks.append(result)
                logger.info(f"Completed {test_name} benchmark")
            except Exception as e:
                logger.error(f"Error in {test_name} benchmark: {e}")
                # Create error result
                error_result = BenchmarkResult(
                    test_name=test_name,
                    old_metrics=[],
                    new_metrics=[],
                    comparison={'error': str(e)},
                    recommendations=[f"Fix benchmark error for {test_name}: {e}"]
                )
                benchmarks.append(error_result)
        
        return benchmarks
    
    def _extract_record_count(self, output: str) -> int:
        """Extract record count from command output"""
        try:
            # Look for common patterns in output
            patterns = [
                'Records processed:',
                'processed',
                'contacts',
                'appointments',
                'records'
            ]
            
            lines = output.lower().split('\n')
            for line in lines:
                for pattern in patterns:
                    if pattern in line:
                        # Extract numbers from the line
                        words = line.split()
                        for word in words:
                            try:
                                # Remove common non-numeric characters
                                cleaned = word.replace(',', '').replace(':', '')
                                if cleaned.isdigit():
                                    return int(cleaned)
                            except:
                                continue
            
            return 0  # Default if no records found
        except:
            return 0
    
    def _compare_metrics(self, old_metrics: List[PerformanceMetrics], 
                        new_metrics: List[PerformanceMetrics]) -> Dict[str, Any]:
        """Compare performance metrics between old and new implementations"""
        comparison = {}
        
        if not old_metrics or not new_metrics:
            comparison['error'] = 'Insufficient data for comparison'
            return comparison
        
        # Calculate averages for successful runs
        old_successful = [m for m in old_metrics if m.success]
        new_successful = [m for m in new_metrics if m.success]
        
        if not old_successful or not new_successful:
            comparison['error'] = 'No successful runs to compare'
            return comparison
        
        # Duration comparison
        old_durations = [m.duration for m in old_successful]
        new_durations = [m.duration for m in new_successful]
        
        comparison['duration'] = {
            'old_avg': mean(old_durations),
            'new_avg': mean(new_durations),
            'old_median': median(old_durations),
            'new_median': median(new_durations),
            'improvement_percent': ((mean(old_durations) - mean(new_durations)) / mean(old_durations) * 100) if mean(old_durations) > 0 else 0
        }
        
        # Memory comparison
        old_memory_deltas = [m.memory_delta for m in old_successful]
        new_memory_deltas = [m.memory_delta for m in new_successful]
        
        comparison['memory'] = {
            'old_avg_delta': mean(old_memory_deltas),
            'new_avg_delta': mean(new_memory_deltas),
            'old_peak_avg': mean([m.memory_peak for m in old_successful]),
            'new_peak_avg': mean([m.memory_peak for m in new_successful]),
            'improvement_percent': ((mean(old_memory_deltas) - mean(new_memory_deltas)) / max(abs(mean(old_memory_deltas)), 1) * 100)
        }
        
        # Throughput comparison
        old_throughput = [m.records_per_second for m in old_successful if m.records_per_second > 0]
        new_throughput = [m.records_per_second for m in new_successful if m.records_per_second > 0]
        
        if old_throughput and new_throughput:
            comparison['throughput'] = {
                'old_avg_rps': mean(old_throughput),
                'new_avg_rps': mean(new_throughput),
                'improvement_percent': ((mean(new_throughput) - mean(old_throughput)) / mean(old_throughput) * 100) if mean(old_throughput) > 0 else 0
            }
        
        # Success rate comparison
        comparison['reliability'] = {
            'old_success_rate': len(old_successful) / len(old_metrics) * 100,
            'new_success_rate': len(new_successful) / len(new_metrics) * 100
        }
        
        # Statistical significance (basic check)
        if len(old_durations) > 2 and len(new_durations) > 2:
            try:
                old_stdev = stdev(old_durations)
                new_stdev = stdev(new_durations)
                comparison['statistics'] = {
                    'old_duration_stdev': old_stdev,
                    'new_duration_stdev': new_stdev,
                    'duration_variance_ratio': new_stdev / old_stdev if old_stdev > 0 else 0
                }
            except:
                pass
        
        return comparison
    
    def _generate_performance_recommendations(self, comparison: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on comparison"""
        recommendations = []
        
        if 'error' in comparison:
            recommendations.append(f"❌ {comparison['error']}")
            return recommendations
        
        # Duration recommendations
        if 'duration' in comparison:
            duration_improvement = comparison['duration']['improvement_percent']
            if duration_improvement > 10:
                recommendations.append(f"✅ New implementation is {duration_improvement:.1f}% faster")
            elif duration_improvement < -10:
                recommendations.append(f"⚠️ New implementation is {abs(duration_improvement):.1f}% slower - investigate performance regression")
            else:
                recommendations.append(f"🔄 Performance is similar (difference: {duration_improvement:.1f}%)")
        
        # Memory recommendations
        if 'memory' in comparison:
            memory_improvement = comparison['memory']['improvement_percent']
            if memory_improvement > 10:
                recommendations.append(f"✅ New implementation uses {memory_improvement:.1f}% less memory")
            elif memory_improvement < -10:
                recommendations.append(f"⚠️ New implementation uses {abs(memory_improvement):.1f}% more memory - investigate memory usage")
        
        # Throughput recommendations
        if 'throughput' in comparison:
            throughput_improvement = comparison['throughput']['improvement_percent']
            if throughput_improvement > 10:
                recommendations.append(f"✅ New implementation has {throughput_improvement:.1f}% better throughput")
            elif throughput_improvement < -10:
                recommendations.append(f"⚠️ New implementation has {abs(throughput_improvement):.1f}% worse throughput")
        
        # Reliability recommendations
        if 'reliability' in comparison:
            old_success = comparison['reliability']['old_success_rate']
            new_success = comparison['reliability']['new_success_rate']
            if new_success > old_success:
                recommendations.append(f"✅ New implementation is more reliable ({new_success:.1f}% vs {old_success:.1f}%)")
            elif new_success < old_success:
                recommendations.append(f"⚠️ New implementation is less reliable ({new_success:.1f}% vs {old_success:.1f}%)")
        
        return recommendations
    
    def generate_benchmark_report(self, benchmarks: List[BenchmarkResult]) -> str:
        """Generate a comprehensive benchmark report"""
        report = []
        report.append("# HubSpot Sync Performance Benchmark Report")
        report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Test Configuration: {self.iterations} iterations, {self.warmup_runs} warmup runs")
        report.append("")
        
        # Executive summary
        report.append("## Executive Summary")
        
        overall_recommendations = []
        for benchmark in benchmarks:
            for rec in benchmark.recommendations:
                if "faster" in rec or "slower" in rec:
                    overall_recommendations.append(f"- {benchmark.test_name}: {rec}")
        
        if overall_recommendations:
            report.extend(overall_recommendations)
        else:
            report.append("- No significant performance differences detected")
        report.append("")
        
        # Detailed results
        for benchmark in benchmarks:
            report.append(f"## {benchmark.test_name.replace('_', ' ').title()} Performance")
            report.append("")
            
            if 'error' in benchmark.comparison:
                report.append(f"❌ Error: {benchmark.comparison['error']}")
                report.append("")
                continue
            
            # Performance metrics table
            if benchmark.old_metrics and benchmark.new_metrics:
                old_successful = [m for m in benchmark.old_metrics if m.success]
                new_successful = [m for m in benchmark.new_metrics if m.success]
                
                if old_successful and new_successful:
                    report.append("### Performance Metrics")
                    report.append("| Metric | Old Implementation | New Implementation | Improvement |")
                    report.append("|--------|-------------------|-------------------|-------------|")
                    
                    # Duration
                    if 'duration' in benchmark.comparison:
                        old_dur = benchmark.comparison['duration']['old_avg']
                        new_dur = benchmark.comparison['duration']['new_avg']
                        improvement = benchmark.comparison['duration']['improvement_percent']
                        report.append(f"| Average Duration | {old_dur:.2f}s | {new_dur:.2f}s | {improvement:+.1f}% |")
                    
                    # Memory
                    if 'memory' in benchmark.comparison:
                        old_mem = benchmark.comparison['memory']['old_avg_delta']
                        new_mem = benchmark.comparison['memory']['new_avg_delta']
                        improvement = benchmark.comparison['memory']['improvement_percent']
                        report.append(f"| Memory Usage | {old_mem:.1f}MB | {new_mem:.1f}MB | {improvement:+.1f}% |")
                    
                    # Throughput
                    if 'throughput' in benchmark.comparison:
                        old_thr = benchmark.comparison['throughput']['old_avg_rps']
                        new_thr = benchmark.comparison['throughput']['new_avg_rps']
                        improvement = benchmark.comparison['throughput']['improvement_percent']
                        report.append(f"| Throughput | {old_thr:.1f} rec/s | {new_thr:.1f} rec/s | {improvement:+.1f}% |")
                    
                    # Success Rate
                    if 'reliability' in benchmark.comparison:
                        old_rel = benchmark.comparison['reliability']['old_success_rate']
                        new_rel = benchmark.comparison['reliability']['new_success_rate']
                        report.append(f"| Success Rate | {old_rel:.1f}% | {new_rel:.1f}% | - |")
                    
                    report.append("")
            
            # Recommendations
            report.append("### Recommendations")
            for rec in benchmark.recommendations:
                report.append(f"- {rec}")
            report.append("")
        
        return "\n".join(report)
