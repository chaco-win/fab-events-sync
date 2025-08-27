#!/usr/bin/env python3
"""
FAB Events Scripts Test Suite
Tests both local and global event scripts to ensure they're working correctly
"""

import os
import sys
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_logging():
    """Setup logging for test results"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # File handler with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_handler = logging.FileHandler(f'logs/test_scripts_{timestamp}.log')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Setup logging
logger = setup_logging()

def check_environment() -> Dict[str, str]:
    """Check if required environment variables are set"""
    logger.info("Checking environment configuration...")
    
    required_vars = {
        'LOCAL_CALENDAR_ID': 'Local DFW Events Calendar',
        'CALENDAR_ID': 'Global Major Events Calendar',
        'SEARCH_LOCATION': 'Search Location for Local Events',
        'FAB_LOCAL_URL': 'Local Events URL',
        'FAB_GLOBAL_URL': 'Global Events URL'
    }
    
    missing_vars = []
    env_status = {}
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            logger.info(f"✅ {var}: {description} - Configured")
            env_status[var] = value
        else:
            logger.warning(f"❌ {var}: {description} - NOT CONFIGURED")
            missing_vars.append(var)
            env_status[var] = None
    
    if missing_vars:
        logger.warning(f"Missing {len(missing_vars)} environment variables")
        logger.warning("Some tests may fail without proper configuration")
    else:
        logger.info("All required environment variables are configured!")
    
    return env_status

def check_dependencies() -> bool:
    """Check if required Python packages are installed"""
    logger.info("Checking Python dependencies...")
    
    required_packages = [
        'requests', 'beautifulsoup4', 'google-api-python-client',
        'google-auth', 'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            logger.info(f"✅ {package} - Installed")
        except ImportError:
            logger.error(f"❌ {package} - NOT INSTALLED")
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"Missing packages: {', '.join(missing_packages)}")
        logger.error("Install with: pip install -r requirements.txt")
        return False
    
    logger.info("All required packages are installed!")
    return True

def check_files() -> bool:
    """Check if required files exist"""
    logger.info("Checking required files...")
    
    required_files = [
        'fab_local_dfw_events.py',
        'fab_major_global_events.py',
        'clean_calendar.py',
        'sa.json',
        'requirements.txt'
    ]
    
    missing_files = []
    
    for file in required_files:
        if os.path.exists(file):
            logger.info(f"✅ {file} - Found")
        else:
            logger.error(f"❌ {file} - NOT FOUND")
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"Missing files: {', '.join(missing_files)}")
        return False
    
    logger.info("All required files are present!")
    return True

def test_script_syntax(script_path: str) -> Tuple[bool, str]:
    """Test if a Python script has valid syntax"""
    try:
        with open(script_path, 'r') as f:
            source = f.read()
        
        compile(source, script_path, 'exec')
        return True, "Syntax OK"
    except SyntaxError as e:
        return False, f"Syntax Error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def test_script_imports(script_path: str) -> Tuple[bool, str]:
    """Test if a Python script can import its dependencies"""
    try:
        # Create a test environment
        test_env = os.environ.copy()
        test_env['PYTHONPATH'] = os.getcwd()
        
        # Try to import the script
        result = subprocess.run([
            sys.executable, '-c', f'import {script_path.replace(".py", "")}'
        ], capture_output=True, text=True, env=test_env, timeout=30)
        
        if result.returncode == 0:
            return True, "Imports OK"
        else:
            return False, f"Import Error: {result.stderr}"
    except subprocess.TimeoutExpired:
        return False, "Import test timed out"
    except Exception as e:
        return False, f"Test Error: {e}"

def run_script_test(script_name: str, script_path: str) -> Dict[str, any]:
    """Run comprehensive tests on a script"""
    logger.info(f"Testing {script_name}...")
    
    results = {
        'script_name': script_name,
        'syntax_test': False,
        'import_test': False,
        'syntax_error': None,
        'import_error': None
    }
    
    # Test syntax
    syntax_ok, syntax_msg = test_script_syntax(script_path)
    results['syntax_test'] = syntax_ok
    if not syntax_ok:
        results['syntax_error'] = syntax_msg
    
    # Test imports
    import_ok, import_msg = test_script_imports(script_path)
    results['import_test'] = import_ok
    if not import_ok:
        results['import_error'] = import_msg
    
    # Log results
    if syntax_ok:
        logger.info(f"✅ {script_name} - Syntax: PASS")
    else:
        logger.error(f"❌ {script_name} - Syntax: FAIL - {syntax_msg}")
    
    if import_ok:
        logger.info(f"✅ {script_name} - Imports: PASS")
    else:
        logger.error(f"❌ {script_name} - Imports: FAIL - {import_msg}")
    
    return results

def run_all_tests() -> List[Dict[str, any]]:
    """Run tests on all scripts"""
    logger.info("=" * 80)
    logger.info("STARTING FAB EVENTS SCRIPTS TEST SUITE")
    logger.info("=" * 80)
    
    # Environment check
    env_status = check_environment()
    
    # Dependencies check
    deps_ok = check_dependencies()
    
    # Files check
    files_ok = check_files()
    
    if not deps_ok or not files_ok:
        logger.error("Prerequisites not met, skipping script tests")
        return []
    
    # Test scripts
    scripts_to_test = [
        ('Local DFW Events Script', 'fab_local_dfw_events.py'),
        ('Global Major Events Script', 'fab_major_global_events.py'),
        ('Calendar Cleaner Script', 'clean_calendar.py')
    ]
    
    test_results = []
    
    for script_name, script_path in scripts_to_test:
        if os.path.exists(script_path):
            results = run_script_test(script_name, script_path)
            test_results.append(results)
        else:
            logger.warning(f"Skipping {script_name} - file not found")
    
    return test_results

def print_test_summary(test_results: List[Dict[str, any]]):
    """Print a summary of all test results"""
    logger.info("=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    total_scripts = len(test_results)
    syntax_passed = sum(1 for r in test_results if r['syntax_test'])
    import_passed = sum(1 for r in test_results if r['import_test'])
    
    logger.info(f"Total Scripts Tested: {total_scripts}")
    logger.info(f"Syntax Tests Passed: {syntax_passed}/{total_scripts}")
    logger.info(f"Import Tests Passed: {import_passed}/{total_scripts}")
    
    if syntax_passed == total_scripts and import_passed == total_scripts:
        logger.info("🎉 ALL TESTS PASSED! Scripts are ready to run.")
    else:
        logger.error("❌ SOME TESTS FAILED! Check the logs above for details.")
    
    # Detailed results
    for result in test_results:
        script_name = result['script_name']
        syntax_status = "✅ PASS" if result['syntax_test'] else "❌ FAIL"
        import_status = "✅ PASS" if result['import_test'] else "❌ FAIL"
        
        logger.info(f"\n{script_name}:")
        logger.info(f"  Syntax: {syntax_status}")
        logger.info(f"  Imports: {import_status}")
        
        if result['syntax_error']:
            logger.error(f"    Syntax Error: {result['syntax_error']}")
        if result['import_error']:
            logger.error(f"    Import Error: {result['import_error']}")

def main():
    """Main test function"""
    try:
        # Run all tests
        test_results = run_all_tests()
        
        # Print summary
        if test_results:
            print_test_summary(test_results)
        else:
            logger.warning("No tests were run")
        
        logger.info("=" * 80)
        logger.info("TEST SUITE COMPLETED")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Test suite failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
