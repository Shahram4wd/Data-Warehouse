"""
Docker environment validation for HubSpot new sync commands
Tests new commands in isolation with comprehensive error checking
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from django.conf import settings
from io import StringIO

from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """Validate new HubSpot sync commands in Docker environment"""
    
    help = "Phase 2: Validate new HubSpot sync commands functionality"
    
    def add_arguments(self, parser):
        """Add command arguments"""
        parser.add_argument(
            "--entity",
            type=str,
            choices=["contacts", "appointments", "divisions", "deals", "associations", "all"],
            default="contacts",
            help="Entity type to validate (default: contacts)"
        )
        parser.add_argument(
            "--dry-run-only",
            action="store_true",
            help="Only run dry-run tests (safer for production)"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10,
            help="Small batch size for testing (default: 10)"
        )
        parser.add_argument(
            "--test-duration",
            type=int,
            default=60,
            help="Maximum test duration in seconds (default: 60)"
        )
        parser.add_argument(
            "--skip-api",
            action="store_true",
            help="Skip tests that require HubSpot API access"
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output from commands"
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        self.stdout.write(self.style.SUCCESS("🚀 Phase 2: Docker Environment Validation"))
        self.stdout.write("=" * 60)
        
        # Check prerequisites
        if not self.check_prerequisites(**options):
            return
        
        entity = options["entity"]
        
        if entity == "all":
            entities = ["contacts", "appointments", "divisions", "deals", "associations"]
        else:
            entities = [entity]
        
        test_results = []
        
        for test_entity in entities:
            self.stdout.write(f"\n🧪 Validating {test_entity.upper()} sync...")
            result = self.validate_entity_command(test_entity, **options)
            test_results.append(result)
        
        # Generate validation report
        self.generate_validation_report(test_results, **options)
    
    def check_prerequisites(self, **options) -> bool:
        """Check if environment is ready for testing"""
        self.stdout.write("🔍 Checking prerequisites...")
        
        issues = []
        
        # Check if HubSpot API token is configured
        if not options.get("skip_api"):
            if not hasattr(settings, 'HUBSPOT_API_TOKEN') or not settings.HUBSPOT_API_TOKEN:
                issues.append("HUBSPOT_API_TOKEN not configured")
        
        # Check if new command files exist
        test_commands = [
            "sync_hubspot_contacts_new",
            "sync_hubspot_appointments_new",
            "sync_hubspot_divisions_new",
            "sync_hubspot_deals_new",
            "sync_hubspot_associations_new"
        ]
        
        for cmd in test_commands:
            try:
                from django.core.management import get_commands
                if cmd not in get_commands():
                    issues.append(f"Command {cmd} not available")
            except Exception as e:
                issues.append(f"Error checking command {cmd}: {e}")
        
        # Check if required models are available
        try:
            from ingestion.models.hubspot import Hubspot_Contact
            from ingestion.models.common import SyncHistory
        except ImportError as e:
            issues.append(f"Required models not available: {e}")
        
        if issues:
            self.stdout.write(self.style.ERROR("❌ Prerequisites check failed:"))
            for issue in issues:
                self.stdout.write(f"  - {issue}")
            return False
        
        self.stdout.write("✅ Prerequisites check passed")
        return True
    
    def validate_entity_command(self, entity: str, **options) -> Dict[str, Any]:
        """Validate a specific entity sync command"""
        command_name = f"sync_hubspot_{entity}_new"
        
        validation_result = {
            "entity": entity,
            "command": command_name,
            "tests": [],
            "overall_success": True,
            "errors": []
        }
        
        # Test 1: Help command
        help_test = self.test_command_help(command_name)
        validation_result["tests"].append(help_test)
        if not help_test["success"]:
            validation_result["overall_success"] = False
        
        # Test 2: Dry run command
        if not options.get("skip_api"):
            dry_run_test = self.test_dry_run(command_name, **options)
            validation_result["tests"].append(dry_run_test)
            if not dry_run_test["success"]:
                validation_result["overall_success"] = False
        
        # Test 3: Import test (check if command can be imported)
        import_test = self.test_command_import(command_name)
        validation_result["tests"].append(import_test)
        if not import_test["success"]:
            validation_result["overall_success"] = False
        
        # Test 4: Quick sync test (only if not dry-run-only)
        if not options.get("dry_run_only") and not options.get("skip_api"):
            quick_test = self.test_quick_sync(command_name, **options)
            validation_result["tests"].append(quick_test)
            if not quick_test["success"]:
                validation_result["overall_success"] = False
        
        return validation_result
    
    def test_command_help(self, command_name: str) -> Dict[str, Any]:
        """Test if command help works"""
        test_result = {
            "test_name": "Help Command",
            "success": False,
            "output": "",
            "error": None,
            "duration": 0
        }
        
        start_time = timezone.now()
        captured_output = StringIO()
        
        try:
            call_command(command_name, "--help", stdout=captured_output, stderr=captured_output)
            output = captured_output.getvalue()
            
            # Check if help output contains expected content
            if "help" in output.lower() and command_name.replace("_", " ") in output.lower():
                test_result["success"] = True
                test_result["output"] = output[:200] + "..." if len(output) > 200 else output
            else:
                test_result["error"] = "Help output doesn't contain expected content"
            
        except Exception as e:
            test_result["error"] = str(e)
            test_result["output"] = captured_output.getvalue()
        finally:
            captured_output.close()
            test_result["duration"] = (timezone.now() - start_time).total_seconds()
        
        return test_result
    
    def test_command_import(self, command_name: str) -> Dict[str, Any]:
        """Test if command can be imported and instantiated"""
        test_result = {
            "test_name": "Import Test",
            "success": False,
            "output": "",
            "error": None,
            "duration": 0
        }
        
        start_time = timezone.now()
        
        try:
            # Try to import the command
            module_path = f"ingestion.management.commands.{command_name}"
            module = __import__(module_path, fromlist=['Command'])
            
            # Try to instantiate the command
            command_class = getattr(module, 'Command')
            command_instance = command_class()
            
            # Check if it has required methods
            required_methods = ['handle', 'add_arguments']
            for method in required_methods:
                if not hasattr(command_instance, method):
                    raise AttributeError(f"Command missing required method: {method}")
            
            test_result["success"] = True
            test_result["output"] = f"Command {command_name} imported and instantiated successfully"
            
        except Exception as e:
            test_result["error"] = str(e)
        finally:
            test_result["duration"] = (timezone.now() - start_time).total_seconds()
        
        return test_result
    
    def test_dry_run(self, command_name: str, **options) -> Dict[str, Any]:
        """Test dry run execution"""
        test_result = {
            "test_name": "Dry Run Test",
            "success": False,
            "output": "",
            "error": None,
            "duration": 0,
            "metrics": {}
        }
        
        start_time = timezone.now()
        captured_output = StringIO()
        
        try:
            # Prepare arguments for dry run
            args = [
                "--dry-run",
                "--batch-size", str(options.get("batch_size", 10)),
                "--debug"
            ]
            
            # Add timeout to prevent hanging
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Command took too long")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(options.get("test_duration", 60))
            
            try:
                call_command(command_name, *args, stdout=captured_output, stderr=captured_output)
                output = captured_output.getvalue()
                
                # Check for success indicators in output
                success_indicators = ["completed", "success", "processed"]
                error_indicators = ["error", "failed", "exception", "traceback"]
                
                has_success = any(indicator in output.lower() for indicator in success_indicators)
                has_error = any(indicator in output.lower() for indicator in error_indicators)
                
                if has_success and not has_error:
                    test_result["success"] = True
                elif has_error:
                    test_result["error"] = "Command output contains error indicators"
                else:
                    test_result["error"] = "Command output unclear - no clear success/error indicators"
                
                test_result["output"] = output[:500] + "..." if len(output) > 500 else output
                
                # Try to extract metrics from output
                test_result["metrics"] = self.extract_metrics_from_output(output)
                
            finally:
                signal.alarm(0)  # Disable the alarm
            
        except TimeoutError:
            test_result["error"] = f"Command timed out after {options.get('test_duration', 60)} seconds"
        except Exception as e:
            test_result["error"] = str(e)
            test_result["output"] = captured_output.getvalue()
        finally:
            captured_output.close()
            test_result["duration"] = (timezone.now() - start_time).total_seconds()
        
        return test_result
    
    def test_quick_sync(self, command_name: str, **options) -> Dict[str, Any]:
        """Test quick sync with very limited scope"""
        test_result = {
            "test_name": "Quick Sync Test",
            "success": False,
            "output": "",
            "error": None,
            "duration": 0,
            "sync_history_id": None
        }
        
        start_time = timezone.now()
        captured_output = StringIO()
        
        try:
            # Use very conservative parameters
            args = [
                "--batch-size", "5",  # Very small batch
                "--since", (timezone.now() - timedelta(days=1)).strftime("%Y-%m-%d"),  # Recent data only
                "--debug"
            ]
            
            # Set timeout
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Quick sync took too long")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(options.get("test_duration", 60))
            
            try:
                call_command(command_name, *args, stdout=captured_output, stderr=captured_output)
                output = captured_output.getvalue()
                
                # Check for sync completion
                if "completed" in output.lower() or "success" in output.lower():
                    test_result["success"] = True
                    
                    # Try to find sync history record
                    entity_type = command_name.replace("sync_hubspot_", "").replace("_new", "")
                    recent_history = SyncHistory.objects.filter(
                        crm_source='hubspot',
                        sync_type=entity_type,
                        start_time__gte=start_time - timedelta(minutes=1)
                    ).order_by('-start_time').first()
                    
                    if recent_history:
                        test_result["sync_history_id"] = recent_history.id
                
                test_result["output"] = output[:500] + "..." if len(output) > 500 else output
                
            finally:
                signal.alarm(0)
            
        except TimeoutError:
            test_result["error"] = f"Quick sync timed out after {options.get('test_duration', 60)} seconds"
        except Exception as e:
            test_result["error"] = str(e)
            test_result["output"] = captured_output.getvalue()
        finally:
            captured_output.close()
            test_result["duration"] = (timezone.now() - start_time).total_seconds()
        
        return test_result
    
    def extract_metrics_from_output(self, output: str) -> Dict[str, Any]:
        """Extract metrics from command output"""
        metrics = {}
        
        import re
        lines = output.split('\n')
        
        for line in lines:
            # Look for common metric patterns
            if 'records processed' in line.lower():
                numbers = re.findall(r'\d+', line)
                if numbers:
                    metrics['records_processed'] = int(numbers[-1])
            elif 'records created' in line.lower():
                numbers = re.findall(r'\d+', line)
                if numbers:
                    metrics['records_created'] = int(numbers[-1])
            elif 'records updated' in line.lower():
                numbers = re.findall(r'\d+', line)
                if numbers:
                    metrics['records_updated'] = int(numbers[-1])
            elif 'duration' in line.lower() and 'second' in line.lower():
                numbers = re.findall(r'\d+\.?\d*', line)
                if numbers:
                    metrics['duration_seconds'] = float(numbers[-1])
        
        return metrics
    
    def generate_validation_report(self, results: List[Dict], **options):
        """Generate and display validation report"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📋 VALIDATION REPORT"))
        self.stdout.write("=" * 60)
        
        total_entities = len(results)
        successful_entities = len([r for r in results if r["overall_success"]])
        
        self.stdout.write(f"\n📊 Summary:")
        self.stdout.write(f"  Total entities tested: {total_entities}")
        self.stdout.write(f"  Successful validations: {successful_entities}")
        self.stdout.write(f"  Success rate: {(successful_entities/total_entities)*100:.1f}%")
        
        # Individual results
        self.stdout.write(f"\n📋 Individual Results:")
        self.stdout.write("-" * 60)
        
        for result in results:
            entity = result["entity"]
            success_icon = "✅" if result["overall_success"] else "❌"
            
            self.stdout.write(f"\n{success_icon} {entity.upper()}:")
            
            for test in result["tests"]:
                test_icon = "✅" if test["success"] else "❌"
                self.stdout.write(f"  {test_icon} {test['test_name']}: {test.get('duration', 0):.2f}s")
                
                if not test["success"] and test.get("error"):
                    self.stdout.write(f"    Error: {test['error']}")
                
                if options.get("verbose") and test.get("output"):
                    output_preview = test["output"][:200] + "..." if len(test["output"]) > 200 else test["output"]
                    self.stdout.write(f"    Output: {output_preview}")
                
                if test.get("metrics"):
                    self.stdout.write(f"    Metrics: {test['metrics']}")
        
        # Overall assessment
        self.stdout.write(f"\n🎯 Assessment:")
        
        if successful_entities == total_entities:
            self.stdout.write("  ✅ All validations passed - new commands are working correctly")
            self.stdout.write("  ✅ Ready for parallel testing with old commands")
        elif successful_entities > 0:
            self.stdout.write(f"  ⚠️  {total_entities - successful_entities} entity(ies) failed validation")
            self.stdout.write("  ⚠️  Review errors before proceeding with parallel testing")
        else:
            self.stdout.write("  ❌ All validations failed - review implementation")
            self.stdout.write("  ❌ Not ready for parallel testing")
        
        # Next steps
        self.stdout.write(f"\n🔄 Next Steps:")
        
        if successful_entities == total_entities:
            self.stdout.write("  1. Run parallel testing: python manage.py hubspot_parallel_test --entity all")
            self.stdout.write("  2. Compare performance and data consistency")
            self.stdout.write("  3. Proceed to Phase 3 migration planning")
        else:
            self.stdout.write("  1. Fix validation errors")
            self.stdout.write("  2. Re-run validation tests")
            self.stdout.write("  3. Then proceed with parallel testing")
        
        self.stdout.write("\n" + "=" * 60)
