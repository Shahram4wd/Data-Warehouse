"""
Quick test script to manually apply JSON normalization to existing records
"""
import os
import sys
import django

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from ingestion.models.salespro import SalesPro_LeadResult
from ingestion.sync.salespro.processors.lead_result import SalesProLeadResultProcessor

def test_manual_normalization():
    """Test manual normalization of existing records"""
    print("=== Manual Lead Result Normalization Test ===\n")
    
    # Initialize processor
    processor = SalesProLeadResultProcessor()
    
    # Get a few records with raw JSON data
    sample_records = SalesPro_LeadResult.objects.filter(
        lead_results_raw__isnull=False,
        lead_results_raw__contains='Appointment Result'
    )[:3]
    
    print(f"Found {sample_records.count()} records with raw JSON data\n")
    
    updated_count = 0
    
    for record in sample_records:
        print(f"Processing record: {record.estimate_id}")
        print(f"Raw data preview: {record.lead_results_raw[:100]}...")
        
        # Create a dict representation for the processor
        record_dict = {
            'estimate_id': record.estimate_id,
            'company_id': record.company_id,
            'lead_results': record.lead_results_raw,  # Use raw data as source
            'created_at': record.created_at,
            'updated_at': record.updated_at,
        }
        
        # Apply normalization
        normalized = processor.normalize_lead_results_json(record.lead_results_raw)
        
        print(f"Normalized fields found: {len(normalized)}")
        for field, value in normalized.items():
            if field != 'lead_results_raw' and value is not None:
                print(f"  {field}: {repr(value)}")
        
        # Update the record
        update_fields = []
        for field, value in normalized.items():
            if hasattr(record, field) and field != 'lead_results_raw':
                setattr(record, field, value)
                update_fields.append(field)
        
        if update_fields:
            record.save(update_fields=update_fields)
            updated_count += 1
            print(f"✅ Updated {len(update_fields)} fields")
        else:
            print("⚠️ No fields to update")
        
        print("-" * 50)
    
    print(f"\n✅ Test completed! Updated {updated_count} records")
    
    # Verify the updates
    print("\n=== Verification ===")
    for record in sample_records:
        record.refresh_from_db()
        print(f"Record {record.estimate_id}:")
        print(f"  appointment_result: {record.appointment_result}")
        print(f"  both_homeowners_present: {record.both_homeowners_present}")
        print(f"  one_year_price: {record.one_year_price}")
        print(f"  last_price_offered: {record.last_price_offered}")

if __name__ == "__main__":
    test_manual_normalization()
