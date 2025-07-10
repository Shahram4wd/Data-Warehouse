"""
Management command to generate comprehensive automation reports for all CRMs.
This command is designed to be run via Celery on a schedule (daily at 9:00 PM and 4:00 AM UTC).
"""
import asyncio
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.conf import settings
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate comprehensive automation reports for all CRMs (HubSpot, Genius, Arrivy)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--time-window',
            type=int,
            default=24,
            help='Time window in hours for metrics collection (default: 24)'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Generate detailed reports with additional metrics'
        )
        parser.add_argument(
            '--crm',
            choices=['hubspot', 'genius', 'arrivy', 'all'],
            default='all',
            help='Generate reports for specific CRM or all (default: all)'
        )
        parser.add_argument(
            '--export-json',
            action='store_true',
            help='Export reports to JSON files'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='logs/automation_reports',
            help='Directory to save JSON exports (default: logs/automation_reports)'
        )

    def handle(self, *args, **options):
        """Main command handler"""
        asyncio.run(self.async_handle(*args, **options))

    async def async_handle(self, *args, **options):
        """Async command handler"""
        time_window = options['time_window']
        detailed = options['detailed']
        crm_filter = options['crm']
        export_json = options['export_json']
        output_dir = options['output_dir']
        
        start_time = timezone.now()
        
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('🤖 GENERATING AUTOMATION REPORTS'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(f"⏰ Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        self.stdout.write(f"🕐 Time window: {time_window} hours")
        self.stdout.write(f"📊 Detailed reports: {'Yes' if detailed else 'No'}")
        self.stdout.write(f"🎯 CRM filter: {crm_filter}")
        
        if export_json:
            import os
            os.makedirs(output_dir, exist_ok=True)
            self.stdout.write(f"💾 JSON exports will be saved to: {output_dir}")
        
        # Define CRMs to process
        crms_to_process = self._get_crms_to_process(crm_filter)
        
        reports = {}
        errors = {}
        
        # Generate reports for each CRM
        for crm_name in crms_to_process:
            self.stdout.write(f"\n{'-'*50}")
            self.stdout.write(f"🔄 Processing {crm_name.upper()} automation reports...")
            
            try:
                report = await self._generate_crm_report(crm_name, time_window, detailed)
                reports[crm_name] = report
                
                # Display summary
                self._display_report_summary(crm_name, report)
                
                # Export to JSON if requested
                if export_json:
                    await self._export_report_to_json(crm_name, report, output_dir)
                
                self.stdout.write(self.style.SUCCESS(f"✅ {crm_name.upper()} report completed"))
                
            except Exception as e:
                error_msg = str(e)
                errors[crm_name] = error_msg
                logger.error(f"Error generating {crm_name} report: {e}", exc_info=True)
                self.stdout.write(self.style.ERROR(f"❌ {crm_name.upper()} report failed: {error_msg}"))
        
        # Generate summary
        await self._generate_final_summary(reports, errors, start_time)

    def _get_crms_to_process(self, crm_filter):
        """Get list of CRMs to process based on filter"""
        all_crms = ['hubspot', 'genius', 'arrivy']
        
        if crm_filter == 'all':
            return all_crms
        else:
            return [crm_filter]

    async def _generate_crm_report(self, crm_name, time_window, detailed):
        """Generate automation report for a specific CRM"""
        try:
            # Import automation system
            from ingestion.base.automation import automation_system
            
            # Get or create automation system for this CRM
            crm_automation = automation_system.get_or_create_system(crm_name)
            
            # Generate comprehensive report
            report = await crm_automation.report_metrics(
                time_window_hours=time_window,
                include_detailed=detailed
            )
            
            return report
            
        except ImportError as e:
            # Fallback if automation system is not available
            logger.warning(f"Automation system not available for {crm_name}: {e}")
            return self._generate_fallback_report(crm_name, time_window)
        except Exception as e:
            logger.error(f"Error generating {crm_name} automation report: {e}")
            raise

    def _generate_fallback_report(self, crm_name, time_window):
        """Generate fallback report when automation system is not available"""
        return {
            'metadata': {
                'source': crm_name,
                'report_generated_at': timezone.now().isoformat(),
                'time_window_hours': time_window,
                'status': 'fallback',
                'note': 'Generated as fallback - automation system not available'
            },
            'performance_metrics': {
                'total_actions': 0,
                'successful_actions': 0,
                'failed_actions': 0,
                'overall_success_rate': 0,
                'actions_per_hour': 0
            },
            'system_health': {
                'active_rules': 0,
                'total_rules': 0,
                'rule_utilization_rate': 0
            },
            'recommendations': [
                {
                    'priority': 'info',
                    'recommendation': 'Automation system is not yet configured for this CRM',
                    'category': 'setup'
                }
            ]
        }

    def _display_report_summary(self, crm_name, report):
        """Display a summary of the generated report"""
        try:
            metadata = report.get('metadata', {})
            performance = report.get('performance_metrics', {})
            health = report.get('system_health', {})
            recommendations = report.get('recommendations', [])
            
            self.stdout.write(f"  📈 Total Actions: {performance.get('total_actions', 0)}")
            self.stdout.write(f"  ✅ Success Rate: {performance.get('overall_success_rate', 0):.1%}")
            self.stdout.write(f"  🔧 Active Rules: {health.get('active_rules', 0)}")
            self.stdout.write(f"  💡 Recommendations: {len(recommendations)}")
            
            # Show top recommendations
            if recommendations:
                self.stdout.write("  🎯 Top Recommendations:")
                for i, rec in enumerate(recommendations[:3], 1):
                    priority = rec.get('priority', 'info').upper()
                    recommendation = rec.get('recommendation', 'No description')
                    self.stdout.write(f"    {i}. [{priority}] {recommendation}")
                    
        except Exception as e:
            self.stdout.write(f"  ⚠️  Error displaying summary: {e}")

    async def _export_report_to_json(self, crm_name, report, output_dir):
        """Export report to JSON file"""
        try:
            import json
            import os
            from datetime import datetime
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{crm_name}_automation_report_{timestamp}.json"
            filepath = os.path.join(output_dir, filename)
            
            # Convert datetime objects to strings for JSON serialization
            json_report = json.dumps(report, indent=2, default=str)
            
            with open(filepath, 'w') as f:
                f.write(json_report)
            
            self.stdout.write(f"  💾 Exported to: {filepath}")
            
        except Exception as e:
            self.stdout.write(f"  ⚠️  Error exporting JSON: {e}")

    async def _generate_final_summary(self, reports, errors, start_time):
        """Generate final summary of all reports"""
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        self.stdout.write(f"\n{'='*70}")
        self.stdout.write(self.style.SUCCESS('📊 AUTOMATION REPORTS SUMMARY'))
        self.stdout.write(f"{'='*70}")
        
        self.stdout.write(f"⏱️  Total Duration: {duration:.2f} seconds")
        self.stdout.write(f"✅ Successful Reports: {len(reports)}")
        self.stdout.write(f"❌ Failed Reports: {len(errors)}")
        
        if reports:
            self.stdout.write(f"\n📈 Overall Statistics:")
            total_actions = sum(r.get('performance_metrics', {}).get('total_actions', 0) for r in reports.values())
            total_rules = sum(r.get('system_health', {}).get('active_rules', 0) for r in reports.values())
            total_recommendations = sum(len(r.get('recommendations', [])) for r in reports.values())
            
            self.stdout.write(f"  🎯 Total Actions Across All CRMs: {total_actions}")
            self.stdout.write(f"  🔧 Total Active Rules: {total_rules}")
            self.stdout.write(f"  💡 Total Recommendations: {total_recommendations}")
        
        if errors:
            self.stdout.write(f"\n❌ Errors:")
            for crm, error in errors.items():
                self.stdout.write(f"  {crm.upper()}: {error}")
        
        # Log completion for monitoring
        logger.info(f"Automation reports generation completed. "
                   f"Success: {len(reports)}, Errors: {len(errors)}, "
                   f"Duration: {duration:.2f}s")
        
        self.stdout.write(self.style.SUCCESS(f"\n🎉 Automation reports generation completed!"))
        self.stdout.write(self.style.SUCCESS('='*70))
