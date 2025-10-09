#!/usr/bin/env python3
"""
Patch ADK to bind to 0.0.0.0 instead of 127.0.0.1
"""
import os
import sys

print("="*70)
print("ADK HOST BINDING PATCHER")
print("="*70)

# Path to ADK CLI tools file (the correct one!)
cli_tools_path = "/usr/local/lib/python3.11/site-packages/google/adk/cli/cli_tools_click.py"

try:
    # Read the original file
    with open(cli_tools_path, 'r') as f:
        content = f.read()
    
    # Check if already patched (check if 0.0.0.0 exists and 127.0.0.1 doesn't)
    if '0.0.0.0' in content and '127.0.0.1' not in content:
        print("✓ ADK already patched for 0.0.0.0 binding")
    else:
        print("Patching ADK cli_tools_click.py...")
        print(f"File size: {len(content)} bytes")
        
        # Replace ALL occurrences of 127.0.0.1 with 0.0.0.0
        original_content = content
        
        # More careful replacement to preserve syntax
        content = content.replace('"127.0.0.1"', '"0.0.0.0"')
        content = content.replace("'127.0.0.1'", "'0.0.0.0'")
        
        if content != original_content:
            # Write back
            with open(cli_tools_path, 'w') as f:
                f.write(content)
            
            print("✓ ADK patched successfully!")
            print(f"✓ Replaced all occurrences of 127.0.0.1 with 0.0.0.0")
        else:
            print("⚠ No replacements made - check pattern matching")
    
    print("="*70)
    print("Starting ADK Web Server...")
    print("="*70)
    
    # Change to agents directory
    os.chdir('/app/agents')
    
    # Use subprocess to call adk command
    import subprocess
    result = subprocess.run(['adk', 'web', '.'], check=False)
    sys.exit(result.returncode)
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
