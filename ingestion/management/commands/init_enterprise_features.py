"""
Management command to initialize enterprise features
"""
import asyncio
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from ingestion.base.connection_pool import initialize_connection_pools
from ingestion.monitoring.alerts import AlertSystem
from ingestion.base.automation import AutomationEngine
from ingestion.base.encryption import CredentialManager

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """Initialize enterprise features for the data warehouse"""
    
    help = "Initialize enterprise features including connection pools, monitoring, and automation"
    
    def add_arguments(self, parser):
        """Add arguments for the initialization command"""
        parser.add_argument(
            "--skip-connection-pools",
            action="store_true",
            help="Skip connection pool initialization"
        )
        parser.add_argument(
            "--skip-monitoring",
            action="store_true",
            help="Skip monitoring system initialization"
        )
        parser.add_argument(
            "--skip-automation",
            action="store_true",
            help="Skip automation engine initialization"
        )
        parser.add_argument(
            "--skip-encryption",
            action="store_true",
            help="Skip encryption system initialization"
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose output"
        )
    
    def handle(self, *args, **options):
        """Main command handler"""
        if options.get('verbose'):
            logging.getLogger().setLevel(logging.DEBUG)
        
        self.stdout.write(self.style.SUCCESS('🚀 Starting enterprise features initialization...'))
        
        # Run async initialization
        asyncio.run(self.async_initialize(**options))
        
        self.stdout.write(self.style.SUCCESS('✅ Enterprise features initialization complete!'))
    
    async def async_initialize(self, **options):
        """Async initialization of enterprise features"""
        
        # Initialize connection pools
        if not options.get('skip_connection_pools'):
            self.stdout.write(self.style.NOTICE('📡 Initializing connection pools...'))
            try:
                await initialize_connection_pools()
                self.stdout.write(self.style.SUCCESS('✓ Connection pools initialized'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Connection pools failed: {e}'))
        
        # Initialize monitoring system
        if not options.get('skip_monitoring'):
            self.stdout.write(self.style.NOTICE('📊 Initializing monitoring system...'))
            try:
                alert_system = AlertSystem()
                await alert_system.initialize()
                self.stdout.write(self.style.SUCCESS('✓ Monitoring system initialized'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Monitoring system failed: {e}'))
        
        # Initialize automation engine
        if not options.get('skip_automation'):
            self.stdout.write(self.style.NOTICE('🤖 Initializing automation engine...'))
            try:
                automation_engine = AutomationEngine('system')
                await automation_engine.initialize()
                self.stdout.write(self.style.SUCCESS('✓ Automation engine initialized'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Automation engine failed: {e}'))
        
        # Initialize encryption system
        if not options.get('skip_encryption'):
            self.stdout.write(self.style.NOTICE('🔐 Initializing encryption system...'))
            try:
                credential_manager = CredentialManager()
                await credential_manager.initialize()
                self.stdout.write(self.style.SUCCESS('✓ Encryption system initialized'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Encryption system failed: {e}'))
        
        # Test all systems
        self.stdout.write(self.style.NOTICE('🔍 Running system health checks...'))
        await self.run_health_checks()
    
    async def run_health_checks(self):
        """Run health checks on all systems"""
        health_status = {
            'connection_pools': False,
            'monitoring': False,
            'automation': False,
            'encryption': False
        }
        
        # Check connection pools
        try:
            from ingestion.base.connection_pool import connection_manager
            stats = connection_manager.get_all_stats()
            if stats:
                health_status['connection_pools'] = True
                self.stdout.write(self.style.SUCCESS('✓ Connection pools healthy'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Connection pools unhealthy: {e}'))
        
        # Check monitoring
        try:
            alert_system = AlertSystem()
            if alert_system.is_healthy():
                health_status['monitoring'] = True
                self.stdout.write(self.style.SUCCESS('✓ Monitoring system healthy'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Monitoring system unhealthy: {e}'))
        
        # Check automation
        try:
            automation_engine = AutomationEngine('system')
            if automation_engine.is_healthy():
                health_status['automation'] = True
                self.stdout.write(self.style.SUCCESS('✓ Automation engine healthy'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Automation engine unhealthy: {e}'))
        
        # Check encryption
        try:
            credential_manager = CredentialManager()
            if credential_manager.is_healthy():
                health_status['encryption'] = True
                self.stdout.write(self.style.SUCCESS('✓ Encryption system healthy'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Encryption system unhealthy: {e}'))
        
        # Overall health report
        healthy_systems = sum(health_status.values())
        total_systems = len(health_status)
        
        self.stdout.write(self.style.NOTICE(f'📊 Health Report: {healthy_systems}/{total_systems} systems healthy'))
        
        if healthy_systems == total_systems:
            self.stdout.write(self.style.SUCCESS('🎉 All systems operational!'))
        elif healthy_systems > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  {total_systems - healthy_systems} system(s) need attention'))
        else:
            self.stdout.write(self.style.ERROR('🚨 All systems are down! Check logs for details.'))
            
        return health_status
