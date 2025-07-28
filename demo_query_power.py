"""
Demo script showing the power of normalized SalesPro Lead Result queries
"""
import os
import sys
import django

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from ingestion.models.salespro import SalesPro_LeadResult
from django.db.models import Q, Count, Avg, Sum
from decimal import Decimal

def demo_powerful_queries():
    """Demonstrate the power of normalized lead result queries"""
    print("🎯 " + "="*60)
    print("  SalesPro Lead Result Normalization - Query Power Demo")
    print("="*60 + " 🎯\n")
    
    # 1. Basic normalization stats
    total_records = SalesPro_LeadResult.objects.count()
    normalized_records = SalesPro_LeadResult.objects.filter(appointment_result__isnull=False).count()
    
    print(f"📊 Database Overview:")
    print(f"   Total lead result records: {total_records:,}")
    print(f"   Records with normalized data: {normalized_records}")
    print(f"   Normalization coverage: {(normalized_records/total_records*100):.2f}%\n")
    
    # 2. Query examples that are now possible
    print("🔥 NEW QUERYING CAPABILITIES:")
    print("-" * 40)
    
    # Query 1: Find demo results by outcome
    print("1️⃣ Demo Results Analysis:")
    demo_sold = SalesPro_LeadResult.objects.filter(
        appointment_result__icontains='Demo Sold'
    ).count()
    demo_not_sold = SalesPro_LeadResult.objects.filter(
        appointment_result__icontains='Demo Not Sold'
    ).count()
    
    if demo_sold > 0 or demo_not_sold > 0:
        print(f"   ✅ Demo Sold: {demo_sold}")
        print(f"   ❌ Demo Not Sold: {demo_not_sold}")
        if demo_sold + demo_not_sold > 0:
            success_rate = (demo_sold / (demo_sold + demo_not_sold)) * 100
            print(f"   📈 Demo Success Rate: {success_rate:.1f}%")
    else:
        print("   No demo result data found yet")
    
    # Query 2: Homeowner presence impact
    print("\n2️⃣ Homeowner Presence Analysis:")
    both_present = SalesPro_LeadResult.objects.filter(
        both_homeowners_present='Yes'
    ).count()
    not_both_present = SalesPro_LeadResult.objects.filter(
        both_homeowners_present='No'
    ).count()
    
    if both_present > 0 or not_both_present > 0:
        print(f"   👥 Both homeowners present: {both_present}")
        print(f"   👤 Not both present: {not_both_present}")
    else:
        print("   No homeowner presence data found yet")
    
    # Query 3: Price analysis
    print("\n3️⃣ Pricing Intelligence:")
    records_with_prices = SalesPro_LeadResult.objects.filter(
        Q(one_year_price__gt=0) | Q(last_price_offered__gt=0)
    )
    
    if records_with_prices.exists():
        avg_one_year = records_with_prices.filter(one_year_price__gt=0).aggregate(
            avg=Avg('one_year_price')
        )['avg']
        avg_last_offer = records_with_prices.filter(last_price_offered__gt=0).aggregate(
            avg=Avg('last_price_offered')
        )['avg']
        
        print(f"   💰 Average one-year price: ${avg_one_year:,.2f}" if avg_one_year else "   💰 No one-year price data")
        print(f"   🏷️ Average last offer: ${avg_last_offer:,.2f}" if avg_last_offer else "   🏷️ No last offer data")
        
        # Price negotiation analysis
        price_diff_records = records_with_prices.filter(
            one_year_price__gt=0, 
            last_price_offered__gt=0
        )
        
        if price_diff_records.exists():
            print(f"   📉 Records with price negotiations: {price_diff_records.count()}")
    else:
        print("   No pricing data found yet")
    
    # Query 4: Objection analysis
    print("\n4️⃣ Objection Pattern Analysis:")
    objections = SalesPro_LeadResult.objects.filter(
        result_reason_demo_not_sold__isnull=False
    ).values('result_reason_demo_not_sold').annotate(
        count=Count('result_reason_demo_not_sold')
    ).order_by('-count')[:3]
    
    if objections:
        print("   🚫 Top objections when demos don't sell:")
        for i, obj in enumerate(objections, 1):
            print(f"      {i}. {obj['result_reason_demo_not_sold']}: {obj['count']} times")
    else:
        print("   No objection data found yet")
    
    # Query 5: Notes search capabilities
    print("\n5️⃣ Search Capabilities in Notes:")
    notes_with_content = SalesPro_LeadResult.objects.filter(
        notes__isnull=False,
        notes__gt=''
    )
    
    if notes_with_content.exists():
        total_notes = notes_with_content.count()
        credit_mentions = notes_with_content.filter(
            notes__icontains='credit'
        ).count()
        finance_mentions = notes_with_content.filter(
            notes__icontains='finance'
        ).count()
        
        print(f"   📝 Records with notes: {total_notes}")
        print(f"   💳 Notes mentioning 'credit': {credit_mentions}")
        print(f"   💰 Notes mentioning 'finance': {finance_mentions}")
    else:
        print("   No notes data found yet")
    
    print("\n" + "="*60)
    print("🚀 BEFORE vs AFTER Normalization:")
    print("="*60)
    
    print("\n❌ BEFORE (JSON blob storage):")
    print("   - Had to parse JSON in every query")
    print("   - No indexing on lead result attributes") 
    print("   - Complex WHERE clauses with JSON functions")
    print("   - Difficult aggregation and reporting")
    print("   - Poor query performance")
    
    print("\n✅ AFTER (Normalized fields):")
    print("   - Direct field queries with indexes")
    print("   - Fast aggregations and analytics")
    print("   - Simple WHERE clauses")
    print("   - Easy reporting and dashboards")
    print("   - Excellent query performance")
    
    # Sample complex queries now possible
    print("\n🔥 COMPLEX QUERIES NOW POSSIBLE:")
    print("-" * 40)
    
    print("   # Find high-value demos that didn't sell due to price")
    print("   SalesPro_LeadResult.objects.filter(")
    print("       appointment_result__icontains='Demo Not Sold',")
    print("       result_reason_demo_not_sold='Too Expensive',")
    print("       last_price_offered__gt=20000")
    print("   )")
    
    print("\n   # Success rate when both homeowners present")
    print("   SalesPro_LeadResult.objects.filter(")
    print("       both_homeowners_present='Yes'")
    print("   ).aggregate(")
    print("       sold=Count('id', filter=Q(appointment_result__icontains='Sold')),")
    print("       total=Count('id')")
    print("   )")
    
    print("\n   # Average discount given in negotiations")
    print("   SalesPro_LeadResult.objects.filter(")
    print("       one_year_price__gt=0,")
    print("       last_price_offered__gt=0")
    print("   ).aggregate(")
    print("       avg_discount=Avg(F('one_year_price') - F('last_price_offered'))")
    print("   )")
    
    print("\n" + "🎯" + "="*58 + "🎯")
    print("  IMPLEMENTATION COMPLETE - JSON NORMALIZATION SUCCESS!")
    print("🎯" + "="*58 + "🎯\n")

if __name__ == "__main__":
    demo_powerful_queries()
