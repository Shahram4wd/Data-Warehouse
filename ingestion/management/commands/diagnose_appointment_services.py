from django.core.management.base import BaseCommand
from ingestion.models.genius import Genius_AppointmentService
from ingestion.models import SyncHistory
from django.db.models import Count


class Command(BaseCommand):
    help = 'Diagnose why db_genius_appointment_services returns zero records'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Genius Appointment Services Sync Diagnosis ==='))
        
        # Check if the target model has any data
        appointment_services_count = Genius_AppointmentService.objects.count()
        self.stdout.write(f'\n📊 Current Data Status:')
        self.stdout.write(f'  Genius_AppointmentService records in Django: {appointment_services_count:,}')
        
        # Check recent sync history
        recent_syncs = SyncHistory.objects.filter(
            crm_source='genius',
            sync_type='appointment_services'
        ).order_by('-start_time')[:5]
        
        self.stdout.write(f'\n🔍 Recent Sync History:')
        if recent_syncs:
            for sync in recent_syncs:
                self.stdout.write(f'  {sync.start_time}: {sync.status} - {sync.records_processed} records')
        else:
            self.stdout.write(f'  No previous syncs found')
        
        # Check what's missing in the sync implementation
        self.stdout.write(f'\n❌ Implementation Issues:')
        
        try:
            from ingestion.sync.genius.clients.appointment_services import GeniusAppointmentServicesClient
            self.stdout.write(f'  ✅ Client exists')
        except ImportError:
            self.stdout.write(f'  ❌ Client missing: GeniusAppointmentServicesClient not found')
        
        try:
            from ingestion.sync.genius.processors.appointment_services import GeniusAppointmentServicesProcessor
            self.stdout.write(f'  ✅ Processor exists')
        except ImportError:
            self.stdout.write(f'  ❌ Processor missing: GeniusAppointmentServicesProcessor not found')
        
        # Check the sync engine implementation
        from ingestion.sync.genius.engines.appointment_services import GeniusAppointmentServicesSyncEngine
        import inspect
        
        engine = GeniusAppointmentServicesSyncEngine()
        source_code = inspect.getsource(engine.execute_sync)
        
        if '# TODO: Implement actual sync logic' in source_code:
            self.stdout.write(f'  ❌ Sync engine not implemented (contains TODO comment)')
        else:
            self.stdout.write(f'  ✅ Sync engine appears to be implemented')
        
        # Show model structure
        self.stdout.write(f'\n📋 Genius_AppointmentService Model Fields:')
        for field in Genius_AppointmentService._meta.get_fields():
            self.stdout.write(f'  - {field.name}: {type(field).__name__}')
        
        # Check if there's source data to sync from
        self.stdout.write(f'\n🔍 Next Steps to Fix:')
        self.stdout.write(f'  1. Create GeniusAppointmentServicesClient to fetch data from Genius DB')
        self.stdout.write(f'  2. Create GeniusAppointmentServicesProcessor to transform data')
        self.stdout.write(f'  3. Implement actual sync logic in GeniusAppointmentServicesSyncEngine')
        self.stdout.write(f'  4. Test with a small dataset first')
        
        self.stdout.write(f'\n💡 The command runs successfully but processes 0 records because:')
        self.stdout.write(f'  - The sync engine only contains a TODO comment')
        self.stdout.write(f'  - No actual database queries are executed')
        self.stdout.write(f'  - It just creates an empty sync record and returns 0 stats')
        
        self.stdout.write('\n' + '='*70)
