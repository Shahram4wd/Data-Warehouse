from django.core.management.base import BaseCommand
from ingestion.models import SalesPro_Appointment, SalesPro_SyncHistory
from django.db.models import Count, Q
from django.db.models.functions import TruncDate


class Command(BaseCommand):
    help = "Explore and analyze SalesPro appointment data"

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed analysis including daily breakdowns'
        )

    def handle(self, *args, **options):
        detailed = options.get('detailed', False)
        
        self.stdout.write(self.style.SUCCESS("=== SALESPRO DATA ANALYSIS ==="))
        
        # Basic stats
        total = SalesPro_Appointment.objects.count()
        sales = SalesPro_Appointment.objects.filter(is_sale=True).count()
        
        self.stdout.write(f"\n📊 OVERVIEW:")
        self.stdout.write(f"   Total Appointments: {total:,}")
        self.stdout.write(f"   Successful Sales: {sales:,}")
        self.stdout.write(f"   Conversion Rate: {(sales/total*100):.1f}%")
        self.stdout.write(f"   No Sales: {total-sales:,}")
        
        # Top performers
        self.stdout.write(f"\n🏆 TOP SALES PERFORMERS:")
        top_reps = (SalesPro_Appointment.objects
                   .filter(is_sale=True)
                   .values('salesrep_first_name', 'salesrep_last_name', 'salesrep_email')
                   .annotate(sales_count=Count('id'))
                   .order_by('-sales_count')[:10])
        
        for i, rep in enumerate(top_reps, 1):
            name = f"{rep['salesrep_first_name']} {rep['salesrep_last_name']}"
            email = rep['salesrep_email'] or 'No email'
            self.stdout.write(f"   {i:2}. {name:<20} - {rep['sales_count']:2} sales ({email})")
        
        # Recent activity
        self.stdout.write(f"\n📅 RECENT ACTIVITY:")
        recent = SalesPro_Appointment.objects.order_by('-created_at')[:10]
        
        for apt in recent:
            status = "✅ SALE" if apt.is_sale else "❌ NO SALE"
            rep_name = f"{apt.salesrep_first_name} {apt.salesrep_last_name}"
            customer_name = f"{apt.customer_first_name} {apt.customer_last_name}"
            date = apt.created_at.strftime('%m/%d %H:%M') if apt.created_at else "No date"
            self.stdout.write(f"   {date} | {status:<10} | {rep_name:<15} -> {customer_name}")
        
        # Import history
        self.stdout.write(f"\n📥 IMPORT HISTORY:")
        syncs = SalesPro_SyncHistory.objects.all().order_by('-started_at')
        
        if syncs:
            for sync in syncs:
                status_icon = "✅" if sync.status == 'completed' else "❌"
                date = sync.started_at.strftime('%Y-%m-%d %H:%M')
                self.stdout.write(f"   {status_icon} {date} | {sync.sync_type} | "
                                f"Created: {sync.records_created}, Updated: {sync.records_updated}")
                if sync.error_message:
                    self.stdout.write(f"      ⚠️  Error: {sync.error_message}")
        else:
            self.stdout.write("   No import history found.")
        
        # Detailed analysis if requested
        if detailed:
            self.stdout.write(f"\n📈 DAILY ACTIVITY (Last 10 Days):")
            daily_stats = (SalesPro_Appointment.objects
                          .filter(created_at__isnull=False)
                          .annotate(date=TruncDate('created_at'))
                          .values('date')
                          .annotate(
                              total_appointments=Count('id'),
                              sales=Count('id', filter=Q(is_sale=True))
                          )
                          .order_by('-date')[:10])
            
            self.stdout.write("   Date       | Apps | Sales | Rate")
            self.stdout.write("   " + "-" * 35)
            for day in daily_stats:
                date = day['date'].strftime('%Y-%m-%d')
                total_day = day['total_appointments']
                sales_day = day['sales']
                rate = (sales_day/total_day*100) if total_day > 0 else 0
                self.stdout.write(f"   {date} | {total_day:4} | {sales_day:5} | {rate:5.1f}%")
            
            # Sales amount analysis
            appointments_with_amounts = SalesPro_Appointment.objects.filter(
                is_sale=True,
                sale_amount__isnull=False,
                sale_amount__gt=0
            )
            
            if appointments_with_amounts.exists():
                from django.db.models import Avg, Sum, Min, Max
                amount_stats = appointments_with_amounts.aggregate(
                    total=Sum('sale_amount'),
                    average=Avg('sale_amount'),
                    min_amount=Min('sale_amount'),
                    max_amount=Max('sale_amount'),
                    count=Count('id')
                )
                
                self.stdout.write(f"\n💰 SALES AMOUNTS:")
                self.stdout.write(f"   Sales with amounts: {amount_stats['count']}")
                self.stdout.write(f"   Total revenue: ${amount_stats['total']:,.2f}")
                self.stdout.write(f"   Average sale: ${amount_stats['average']:,.2f}")
                self.stdout.write(f"   Min sale: ${amount_stats['min_amount']:,.2f}")
                self.stdout.write(f"   Max sale: ${amount_stats['max_amount']:,.2f}")
        
        self.stdout.write(f"\n✅ Analysis complete!")
        if not detailed:
            self.stdout.write("   Use --detailed for more comprehensive analysis")
