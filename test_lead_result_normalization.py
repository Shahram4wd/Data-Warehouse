"""
Test script for SalesPro Lead Result JSON normalization
This demonstrates how the processor converts JSON lead_results to separate fields
"""
import sys
import json
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Sample lead_results JSON from user's example
sample_lead_results = """[
    {"title": "Appointment Result", "value": "Demo - Not Sold"},
    {"title": "Result Reason - Demo Not Sold (objection)", "value": "-Undecided"},
    {"title": "Result Reason - No Demo (REQUIRES SALES MANGER APPROVAL)", "value": ""},
    {"title": "Both Homeowners Present?", "value": "Yes"},
    {"title": "One Year Price", "value": "$0.00"},
    {"title": "Last Price Offered", "value": "$0.00"},
    {"title": "Preferred Payment ", "value": ""},
    {"title": "Notes", "value": "Both homeowners were present. Homeowner has been thinking about this for a while and when they purchased their home 2 years ago they were going to put solar on shortly thereafter. Homeowner wants to think about it a little bit longer because he wants to look at his utility bill for the last year to see what his actual power consumption is and verify whether our calculations are accurate."}
]"""

def test_json_normalization():
    """Test the JSON normalization logic"""
    
    # Simulate the processor logic
    print("=== SalesPro Lead Result JSON Normalization Test ===\n")
    
    print("Sample JSON input:")
    print(sample_lead_results)
    print("\n" + "="*60 + "\n")
    
    # Parse the JSON
    try:
        lead_data = json.loads(sample_lead_results)
        print("Parsed JSON structure:")
        for item in lead_data:
            print(f"  {item['title']} -> {item['value']}")
        print("\n" + "="*60 + "\n")
        
        # Simulate normalization
        title_mappings = {
            "Appointment Result": "appointment_result",
            "Result Reason - Demo Not Sold (objection)": "result_reason_demo_not_sold",
            "Result Reason - No Demo (REQUIRES SALES MANGER APPROVAL)": "result_reason_no_demo",
            "Both Homeowners Present?": "both_homeowners_present",
            "One Year Price": "one_year_price",
            "Last Price Offered": "last_price_offered",
            "Preferred Payment": "preferred_payment",
            "Preferred Payment ": "preferred_payment",  # Handle extra space variant
            "Notes": "notes",
        }
        
        normalized = {}
        
        for item in lead_data:
            if isinstance(item, dict) and 'title' in item and 'value' in item:
                title = item['title']
                value = item['value']
                
                if title in title_mappings:
                    field_name = title_mappings[title]
                    
                    # Handle price fields
                    if field_name in ['one_year_price', 'last_price_offered']:
                        # Remove currency symbols and convert to decimal
                        import re
                        clean_price = re.sub(r'[^\d.-]', '', str(value))
                        if clean_price and clean_price != '-':
                            try:
                                from decimal import Decimal
                                normalized[field_name] = Decimal(clean_price)
                            except:
                                normalized[field_name] = None
                        else:
                            normalized[field_name] = None
                    else:
                        # Clean text values
                        cleaned = str(value).strip() if value else None
                        if cleaned and cleaned.lower() not in ['', 'null', 'none', 'n/a', '-']:
                            # Handle values that start with dashes
                            if cleaned.startswith('-') and len(cleaned) > 1:
                                cleaned = cleaned[1:].strip()
                            normalized[field_name] = cleaned if cleaned else None
                        else:
                            normalized[field_name] = None
        
        # Add raw backup
        normalized['lead_results_raw'] = sample_lead_results
        
        print("Normalized fields:")
        for field, value in normalized.items():
            if field != 'lead_results_raw':
                print(f"  {field}: {repr(value)}")
        
        print(f"\nRaw backup stored in: lead_results_raw")
        print(f"Total normalized fields: {len(normalized) - 1}")  # Exclude raw backup
        
        print("\n" + "="*60 + "\n")
        print("Database query examples after normalization:")
        print("  # Find all demos that weren't sold")
        print("  SalesPro_LeadResult.objects.filter(appointment_result__icontains='Demo - Not Sold')")
        print()
        print("  # Find all cases where both homeowners were present")  
        print("  SalesPro_LeadResult.objects.filter(both_homeowners_present='Yes')")
        print()
        print("  # Find all records with notes containing specific keywords")
        print("  SalesPro_LeadResult.objects.filter(notes__icontains='utility bill')")
        print()
        print("  # Find records where prices were offered")
        print("  SalesPro_LeadResult.objects.filter(one_year_price__gt=0)")
        
        return normalized
        
    except Exception as e:
        print(f"Error processing JSON: {e}")
        return None

if __name__ == "__main__":
    test_json_normalization()
