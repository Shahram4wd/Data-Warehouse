"""
Phase 2: Parallel testing framework for HubSpot sync commands
Runs both old and new commands and compares results within Docker environment
"""
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from django.db import transaction
from io import StringIO
import sys

from ingestion.models.common import SyncHistory
from ingestion.models.hubspot import Hubspot_Contact, Hubspot_Appointment, Hubspot_Division, Hubspot_Deal

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """Run parallel testing of old vs new HubSpot sync commands"""
    
    help = "Phase 2: Run parallel testing of old vs new HubSpot sync commands"
    
    def add_arguments(self, parser):
        """Add command arguments"""
        parser.add_argument(
            "--entity",
            type=str,
            choices=["contacts", "appointments", "divisions", "deals", "all"],
            default="contacts",
            help="Entity type to test (default: contacts)"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run both commands in dry-run mode"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="Batch size for testing (default: 50)"
        )
        parser.add_argument(
            "--since",
            type=str,
            help="Test with data since this date (YYYY-MM-DD)"
        )
        parser.add_argument(
            "--skip-old",
            action="store_true",
            help="Skip running old commands (only test new)"
        )
        parser.add_argument(
            "--skip-new",
            action="store_true",
            help="Skip running new commands (only test old)"
        )
        parser.add_argument(
            "--compare-data",
            action="store_true",
            help="Compare actual data results between old and new"
        )
        parser.add_argument(
            "--report-file",
            type=str,
            help="Save detailed report to file"
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        self.stdout.write(self.style.SUCCESS("🚀 Phase 2: HubSpot Parallel Testing"))
        self.stdout.write("=" * 60)
        
        entity = options["entity"]
        
        if entity == "all":
            entities = ["contacts", "appointments", "divisions", "deals"]
        else:
            entities = [entity]
        
        overall_results = []
        
        for test_entity in entities:
            self.stdout.write(f"\n📊 Testing {test_entity.upper()} sync...")
            result = self.test_entity_sync(test_entity, **options)
            overall_results.append(result)
        
        # Generate final report
        self.generate_final_report(overall_results, **options)
    
    def test_entity_sync(self, entity: str, **options) -> Dict[str, Any]:
        """Test sync for a specific entity"""
        test_start = timezone.now()
        
        # Get command mappings
        old_command, new_command = self.get_command_mapping(entity)
        
        # Prepare command arguments
        cmd_args = []
        if options.get("dry_run"):
            cmd_args.append("--dry-run")
        if options.get("batch_size"):
            cmd_args.extend(["--batch-size", str(options["batch_size"])])
        if options.get("since"):
            cmd_args.extend(["--since", options["since"]])
        
        results = {
            "entity": entity,
            "test_start": test_start,
            "old_command": old_command,
            "new_command": new_command,
            "old_result": None,
            "new_result": None,
            "comparison": None,
            "errors": []
        }
        
        # Run old command
        if not options.get("skip_old") and old_command:
            self.stdout.write(f"  🔄 Running OLD command: {old_command}")
            try:
                old_result = self.run_command_with_capture(old_command, cmd_args)
                results["old_result"] = old_result
                self.stdout.write(f"    ✅ OLD command completed")
            except Exception as e:
                error_msg = f"OLD command failed: {str(e)}"
                self.stdout.write(self.style.ERROR(f"    ❌ {error_msg}"))
                results["errors"].append(error_msg)
        
        # Run new command
        if not options.get("skip_new") and new_command:
            self.stdout.write(f"  🔄 Running NEW command: {new_command}")
            try:
                new_result = self.run_command_with_capture(new_command, cmd_args)
                results["new_result"] = new_result
                self.stdout.write(f"    ✅ NEW command completed")
            except Exception as e:
                error_msg = f"NEW command failed: {str(e)}"
                self.stdout.write(self.style.ERROR(f"    ❌ {error_msg}"))
                results["errors"].append(error_msg)
        
        # Compare results
        if results["old_result"] and results["new_result"]:
            self.stdout.write(f"  📊 Comparing results...")
            comparison = self.compare_results(entity, results["old_result"], results["new_result"])
            results["comparison"] = comparison
            
            if comparison["data_consistent"]:
                self.stdout.write(f"    ✅ Data consistency: PASSED")
            else:
                self.stdout.write(f"    ⚠️  Data consistency: DIFFERENCES FOUND")
            
            # Performance comparison
            old_duration = results["old_result"].get("duration", 0)
            new_duration = results["new_result"].get("duration", 0)
            
            if new_duration > 0 and old_duration > 0:
                improvement = ((old_duration - new_duration) / old_duration) * 100
                if improvement > 0:
                    self.stdout.write(f"    ⚡ Performance: {improvement:.1f}% faster")
                else:
                    self.stdout.write(f"    ⚠️  Performance: {abs(improvement):.1f}% slower")
        
        # Data comparison if requested
        if options.get("compare_data") and not options.get("dry_run"):
            self.stdout.write(f"  🔍 Performing detailed data comparison...")
            data_comparison = self.compare_database_data(entity, test_start)
            results["data_comparison"] = data_comparison
        
        results["test_end"] = timezone.now()
        results["test_duration"] = (results["test_end"] - test_start).total_seconds()
        
        return results
    
    def get_command_mapping(self, entity: str) -> Tuple[str, str]:
        """Get old and new command names for entity"""
        mappings = {
            "contacts": ("sync_hubspot_contacts", "sync_hubspot_contacts_new"),
            "appointments": ("sync_hubspot_appointments", "sync_hubspot_appointments_new"),
            "divisions": ("sync_hubspot_divisions", "sync_hubspot_divisions_new"),
            "deals": ("sync_hubspot_deals", "sync_hubspot_deals_new"),
        }
        return mappings.get(entity, (None, None))
    
    def run_command_with_capture(self, command: str, args: List[str]) -> Dict[str, Any]:
        """Run a command and capture its output and metrics"""
        start_time = timezone.now()
        
        # Capture stdout
        captured_output = StringIO()
        
        try:
            # Run the command
            call_command(command, *args, stdout=captured_output)
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            # Get the output
            output = captured_output.getvalue()
            
            # Try to extract metrics from output or sync history
            metrics = self.extract_metrics_from_output(output, command, start_time)
            
            return {
                "command": command,
                "args": args,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "output": output,
                "success": True,
                "metrics": metrics
            }
            
        except Exception as e:
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "command": command,
                "args": args,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "output": captured_output.getvalue(),
                "success": False,
                "error": str(e),
                "metrics": {}
            }
        finally:
            captured_output.close()
    
    def extract_metrics_from_output(self, output: str, command: str, start_time: datetime) -> Dict[str, Any]:
        """Extract metrics from command output or sync history"""
        metrics = {
            "records_processed": 0,
            "records_created": 0,
            "records_updated": 0,
            "records_failed": 0
        }
        
        # Try to extract from output text
        lines = output.split('\n')
        for line in lines:
            if 'processed' in line.lower():
                # Try to extract numbers from the line
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    metrics["records_processed"] = int(numbers[0])
            elif 'created' in line.lower():
                numbers = re.findall(r'\d+', line)
                if numbers:
                    metrics["records_created"] = int(numbers[0])
            elif 'updated' in line.lower():
                numbers = re.findall(r'\d+', line)
                if numbers:
                    metrics["records_updated"] = int(numbers[0])
        
        # Try to get from sync history for new commands
        if "_new" in command:
            try:
                # Extract entity type from command
                entity_type = command.replace("sync_hubspot_", "").replace("_new", "")
                
                history = SyncHistory.objects.filter(
                    crm_source='hubspot',
                    sync_type=entity_type,
                    start_time__gte=start_time - timedelta(minutes=1)
                ).order_by('-start_time').first()
                
                if history:
                    metrics.update({
                        "records_processed": history.records_processed,
                        "records_created": history.records_created,
                        "records_updated": history.records_updated,
                        "records_failed": history.records_failed
                    })
                    
            except Exception as e:
                logger.warning(f"Could not extract metrics from sync history: {e}")
        
        return metrics
    
    def compare_results(self, entity: str, old_result: Dict, new_result: Dict) -> Dict[str, Any]:
        """Compare results between old and new commands"""
        old_metrics = old_result.get("metrics", {})
        new_metrics = new_result.get("metrics", {})
        
        comparison = {
            "data_consistent": True,
            "performance_improvement": 0,
            "differences": [],
            "old_metrics": old_metrics,
            "new_metrics": new_metrics
        }
        
        # Compare record counts
        for metric in ["records_processed", "records_created", "records_updated"]:
            old_val = old_metrics.get(metric, 0)
            new_val = new_metrics.get(metric, 0)
            
            # Allow for small differences (within 5%)
            if old_val > 0:
                diff_pct = abs(old_val - new_val) / old_val * 100
                if diff_pct > 5:
                    comparison["data_consistent"] = False
                    comparison["differences"].append(
                        f"{metric}: OLD={old_val}, NEW={new_val} ({diff_pct:.1f}% difference)"
                    )
        
        # Compare performance
        old_duration = old_result.get("duration", 0)
        new_duration = new_result.get("duration", 0)
        
        if old_duration > 0 and new_duration > 0:
            improvement = ((old_duration - new_duration) / old_duration) * 100
            comparison["performance_improvement"] = improvement
        
        return comparison
    
    def compare_database_data(self, entity: str, test_start: datetime) -> Dict[str, Any]:
        """Compare actual database data between syncs"""
        model_map = {
            "contacts": Hubspot_Contact,
            "appointments": Hubspot_Appointment,
            "divisions": Hubspot_Division,
            "deals": Hubspot_Deal
        }
        
        model = model_map.get(entity)
        if not model:
            return {"error": f"Unknown entity: {entity}"}
        
        try:
            # Get recent records (created/updated since test start)
            recent_records = model.objects.filter(
                lastmodifieddate__gte=test_start - timedelta(hours=1)
            ).count()
            
            # Get total records
            total_records = model.objects.count()
            
            return {
                "total_records": total_records,
                "recent_records": recent_records,
                "test_start": test_start
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def generate_final_report(self, results: List[Dict], **options):
        """Generate and display final test report"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📋 PHASE 2 TESTING REPORT"))
        self.stdout.write("=" * 60)
        
        # Summary
        total_tests = len(results)
        successful_tests = len([r for r in results if not r["errors"]])
        consistent_tests = len([r for r in results if r.get("comparison", {}).get("data_consistent", False)])
        
        self.stdout.write(f"\n📊 Summary:")
        self.stdout.write(f"  Total entity tests: {total_tests}")
        self.stdout.write(f"  Successful tests: {successful_tests}")
        self.stdout.write(f"  Data consistent tests: {consistent_tests}")
        
        # Individual results
        self.stdout.write(f"\n📋 Individual Results:")
        self.stdout.write("-" * 60)
        
        for result in results:
            entity = result["entity"]
            self.stdout.write(f"\n🔍 {entity.upper()}:")
            
            if result["errors"]:
                for error in result["errors"]:
                    self.stdout.write(self.style.ERROR(f"  ❌ {error}"))
            else:
                # Performance comparison
                if result.get("comparison"):
                    improvement = result["comparison"].get("performance_improvement", 0)
                    if improvement > 0:
                        self.stdout.write(f"  ⚡ Performance: {improvement:.1f}% faster")
                    else:
                        self.stdout.write(f"  ⚠️  Performance: {abs(improvement):.1f}% slower")
                    
                    # Data consistency
                    if result["comparison"]["data_consistent"]:
                        self.stdout.write(f"  ✅ Data consistency: PASSED")
                    else:
                        self.stdout.write(f"  ⚠️  Data consistency: ISSUES FOUND")
                        for diff in result["comparison"]["differences"]:
                            self.stdout.write(f"    - {diff}")
                
                # Metrics
                if result.get("old_result"):
                    old_metrics = result["old_result"]["metrics"]
                    self.stdout.write(f"  📊 OLD: {old_metrics.get('records_processed', 0)} processed")
                
                if result.get("new_result"):
                    new_metrics = result["new_result"]["metrics"]
                    self.stdout.write(f"  📊 NEW: {new_metrics.get('records_processed', 0)} processed")
        
        # Recommendations
        self.stdout.write(f"\n💡 Recommendations:")
        
        if consistent_tests == total_tests:
            self.stdout.write("  ✅ All tests passed - ready for Phase 3 migration")
        else:
            self.stdout.write("  ⚠️  Some tests failed - review issues before migration")
        
        # Performance summary
        improvements = [r.get("comparison", {}).get("performance_improvement", 0) for r in results 
                       if r.get("comparison")]
        if improvements:
            avg_improvement = sum(improvements) / len(improvements)
            if avg_improvement > 0:
                self.stdout.write(f"  ⚡ Average performance improvement: {avg_improvement:.1f}%")
            else:
                self.stdout.write(f"  ⚠️  Average performance regression: {abs(avg_improvement):.1f}%")
        
        # Save detailed report if requested
        if options.get("report_file"):
            self.save_detailed_report(results, options["report_file"])
            self.stdout.write(f"  📄 Detailed report saved to: {options['report_file']}")
        
        self.stdout.write("\n" + "=" * 60)
    
    def save_detailed_report(self, results: List[Dict], filename: str):
        """Save detailed report to file"""
        report_data = {
            "test_timestamp": timezone.now().isoformat(),
            "total_tests": len(results),
            "results": []
        }
        
        for result in results:
            # Clean up datetime objects for JSON serialization
            clean_result = {}
            for key, value in result.items():
                if isinstance(value, datetime):
                    clean_result[key] = value.isoformat()
                elif key in ["old_result", "new_result"] and value:
                    clean_value = {}
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, datetime):
                            clean_value[sub_key] = sub_value.isoformat()
                        else:
                            clean_value[sub_key] = sub_value
                    clean_result[key] = clean_value
                else:
                    clean_result[key] = value
            
            report_data["results"].append(clean_result)
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)
