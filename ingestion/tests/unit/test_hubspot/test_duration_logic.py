#!/usr/bin/env python3
"""
Direct test for duration parsing logic
"""
import re

def parse_duration(duration_str):
    """Parse duration string in HH:MM:SS format to integer minutes"""
    if not duration_str:
        return 0
    
    try:
        # Match HH:MM:SS pattern
        match = re.match(r'(\d{1,2}):(\d{2}):(\d{2})', str(duration_str))
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            
            # Convert to total minutes
            total_minutes = hours * 60 + minutes + (seconds // 60)
            return total_minutes
        else:
            return 0
    except (ValueError, AttributeError):
        return 0

def test_parse_duration():
    """Test parse_duration method"""
    print("Testing parse_duration method...")
    
    # Test cases
    test_cases = [
        ("01:30:00", 90),  # 1 hour 30 minutes
        ("02:00:00", 120),  # 2 hours
        ("00:30:00", 30),   # 30 minutes
        ("00:15:00", 15),   # 15 minutes
        ("03:45:00", 225),  # 3 hours 45 minutes
        ("24:00:00", 1440), # 24 hours
        ("", 0),            # Empty string
        (None, 0),          # None value
        ("invalid", 0),     # Invalid format
        ("1:30:00", 90),    # Without leading zero
    ]
    
    for input_duration, expected_minutes in test_cases:
        result = parse_duration(input_duration)
        print(f"Input: '{input_duration}' -> Expected: {expected_minutes}, Got: {result}")
        assert result == expected_minutes, f"Failed for input '{input_duration}': expected {expected_minutes}, got {result}"
    
    print("✓ All parse_duration tests passed!")

if __name__ == "__main__":
    try:
        test_parse_duration()
        print("\n🎉 Duration parsing logic test passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
