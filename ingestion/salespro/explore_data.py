#!/usr/bin/env python
"""
Quick data exploration script for SalesPro appointments
Run this from inside the Django shell or as a management command
"""

import django
import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from ingestion.models import SalesPro_Appointment, SalesPro_SyncHistory
from django.db.models import Count, Avg, Sum, Q
from collections import Counter


def print_separator(title=""):
    print("=" * 60)
    if title:
        print(f" {title} ")
        print("=" * 60)


def basic_stats():
    """Print basic statistics about the SalesPro data"""
    print_separator("SALESPRO APPOINTMENTS - BASIC STATISTICS")
    
    total = SalesPro_Appointment.objects.count()
    sales = SalesPro_Appointment.objects.filter(is_sale=True).count()
    
    print(f"Total Appointments: {total:,}")
    print(f"Successful Sales: {sales:,}")
    print(f"Sales Conversion Rate: {(sales/total*100):.1f}%")
    print(f"Non-Sales: {total-sales:,}")


def top_performers():
    """Show top performing sales reps"""
    print_separator("TOP SALES PERFORMERS")
    
    # Top sales reps by number of sales
    top_by_sales = (SalesPro_Appointment.objects
                   .filter(is_sale=True)
                   .values('salesrep_first_name', 'salesrep_last_name', 'salesrep_email')
                   .annotate(sales_count=Count('id'))
                   .order_by('-sales_count')[:10])
    
    print("Top 10 Sales Reps by Number of Sales:")
    for i, rep in enumerate(top_by_sales, 1):
        name = f"{rep['salesrep_first_name']} {rep['salesrep_last_name']}"
        print(f"{i:2}. {name:<25} - {rep['sales_count']} sales ({rep['salesrep_email']})")


def recent_activity():
    """Show recent appointment activity"""
    print_separator("RECENT ACTIVITY")
    
    recent = (SalesPro_Appointment.objects
             .order_by('-created_at')[:10])
    
    print("10 Most Recent Appointments:")
    for apt in recent:
        status = "SALE" if apt.is_sale else "NO SALE"
        rep_name = f"{apt.salesrep_first_name} {apt.salesrep_last_name}"
        customer_name = f"{apt.customer_first_name} {apt.customer_last_name}"
        date = apt.created_at.strftime('%Y-%m-%d %H:%M') if apt.created_at else "No date"
        print(f"- {date} | {status:<7} | {rep_name:<20} -> {customer_name}")


def sync_history():
    """Show import history"""
    print_separator("IMPORT HISTORY")
    
    syncs = SalesPro_SyncHistory.objects.all().order_by('-started_at')
    
    if syncs:
        print("Import History:")
        for sync in syncs:
            status_icon = "✓" if sync.status == 'completed' else "✗"
            date = sync.started_at.strftime('%Y-%m-%d %H:%M:%S')
            print(f"{status_icon} {date} | {sync.sync_type} | "
                  f"Processed: {sync.records_processed}, "
                  f"Created: {sync.records_created}, "
                  f"Updated: {sync.records_updated}")
            if sync.error_message:
                print(f"   Error: {sync.error_message}")
    else:
        print("No import history found.")


def daily_activity():
    """Show appointment activity by day"""
    print_separator("DAILY ACTIVITY SUMMARY")
    
    # Count appointments by date
    from django.db.models.functions import TruncDate
    daily_stats = (SalesPro_Appointment.objects
                  .filter(created_at__isnull=False)
                  .annotate(date=TruncDate('created_at'))
                  .values('date')
                  .annotate(
                      total_appointments=Count('id'),
                      sales=Count('id', filter=Q(is_sale=True))
                  )
                  .order_by('-date')[:10])
    
    print("Last 10 Days with Activity:")
    print("Date       | Appointments | Sales | Conversion Rate")
    print("-" * 50)
    for day in daily_stats:
        date = day['date'].strftime('%Y-%m-%d')
        total = day['total_appointments']
        sales = day['sales']
        rate = (sales/total*100) if total > 0 else 0
        print(f"{date} | {total:11} | {sales:5} | {rate:11.1f}%")


if __name__ == "__main__":
    print("SalesPro Data Explorer")
    print("Run this script to see statistics about your imported SalesPro data")
    print()
    
    try:
        basic_stats()
        print()
        top_performers()
        print()
        recent_activity()
        print()
        daily_activity()
        print()
        sync_history()
        print()
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have imported SalesPro data first using the database sync commands.")
