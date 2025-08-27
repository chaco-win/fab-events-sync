#!/usr/bin/env python3
"""
Simple Test Runner for FAB Events Scripts
Quick way to test if scripts are working
"""

import subprocess
import sys
import os

def run_test(script_name: str, description: str):
    """Run a simple test on a script"""
    print(f"\n{'='*60}")
    print(f"Testing: {script_name}")
    print(f"Description: {description}")
    print(f"{'='*60}")
    
    try:
        # Test if script can be imported
        result = subprocess.run([
            sys.executable, '-c', f'import {script_name.replace(".py", "")}'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"✅ {script_name} - Import test PASSED")
            return True
        else:
            print(f"❌ {script_name} - Import test FAILED")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ {script_name} - Import test TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ {script_name} - Import test ERROR: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 FAB Events Scripts - Quick Test Runner")
    print("This will test if the scripts can be imported without errors")
    
    scripts_to_test = [
        ('fab_local_dfw_events.py', 'Local DFW Events Scraper'),
        ('fab_major_global_events.py', 'Global Major Events Scraper'),
        ('clean_calendar.py', 'Calendar Cleaner'),
        ('test_scripts.py', 'Test Suite')
    ]
    
    passed = 0
    total = len(scripts_to_test)
    
    for script_name, description in scripts_to_test:
        if os.path.exists(script_name):
            if run_test(script_name, description):
                passed += 1
        else:
            print(f"\n❌ {script_name} - FILE NOT FOUND")
    
    print(f"\n{'='*60}")
    print("TEST RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Scripts are ready to run.")
    else:
        print("❌ SOME TESTS FAILED! Check the errors above.")
    
    print(f"\nNext steps:")
    print("1. Set up your .env file with calendar IDs")
    print("2. Run: python clean_calendar.py (to clean calendars)")
    print("3. Run: python fab_local_dfw_events.py (test local script)")
    print("4. Run: python fab_major_global_events.py (test global script)")

if __name__ == "__main__":
    main()
