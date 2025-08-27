#!/usr/bin/env python3
"""
Health Check Script for FAB Events Sync System

This script runs weekly on Tuesday to verify the system is ready
for Wednesday's event synchronization runs.

Author: FAB Events Sync System
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# Configure logging
def setup_logging() -> logging.Logger:
    """Set up logging configuration for the health check script."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"health_check_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def check_container_status() -> bool:
    """Check if the Docker container is running."""
    try:
        # Simple check - if we can access the /app directory, container is running
        app_dir = Path("/app")
        if app_dir.exists() and app_dir.is_dir():
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking container status: {e}")
        return False

def check_log_files() -> bool:
    """Check if log files have been updated recently (within last 7 days)."""
    try:
        log_dir = Path("logs")
        if not log_dir.exists():
            logger.error("Logs directory not found")
            return False
        
        # Check for recent log files
        current_time = datetime.now()
        recent_logs = 0
        
        for log_file in log_dir.glob("*.log"):
            if log_file.is_file():
                file_age = current_time - datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_age.days < 7:
                    recent_logs += 1
        
        if recent_logs > 0:
            logger.info(f"Found {recent_logs} recent log files")
            return True
        else:
            logger.error("No recent log files found")
            return False
            
    except Exception as e:
        logger.error(f"Error checking log files: {e}")
        return False

def check_google_calendar_api() -> bool:
    """Check if Google Calendar API is accessible."""
    try:
        # Import required modules
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        # Check if credentials file exists
        creds_file = Path("sa.json")
        if not creds_file.exists():
            logger.error("Service account credentials file not found")
            return False
        
        # Try to load credentials
        creds = Credentials.from_service_account_file("sa.json")
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                logger.error("Invalid or expired credentials")
                return False
        
        # Try to build the service
        service = build('calendar', 'v3', credentials=creds)
        
        # Simple API call to test connectivity
        calendar_list = service.calendarList().list(maxResults=1).execute()
        
        logger.info("Google Calendar API is accessible")
        return True
        
    except ImportError as e:
        logger.error(f"Required Google API modules not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Error testing Google Calendar API: {e}")
        return False

def check_required_scripts() -> bool:
    """Check if all required Python scripts are present."""
    try:
        required_scripts = [
            "fab_local_dfw_events.py",
            "fab_major_global_events.py",
            "clean_calendar.py",
            "test_scripts.py",
            "view_logs.py"
        ]
        
        missing_scripts = []
        for script in required_scripts:
            if not Path(script).exists():
                missing_scripts.append(script)
        
        if missing_scripts:
            logger.error(f"Missing required scripts: {missing_scripts}")
            return False
        
        logger.info("All required scripts are present")
        return True
        
    except Exception as e:
        logger.error(f"Error checking required scripts: {e}")
        return False

def run_health_check() -> Dict[str, bool]:
    """Run all health checks and return results."""
    logger.info("Starting FAB Events Sync System Health Check")
    logger.info("=" * 50)
    
    checks = {
        "Container Status": check_container_status(),
        "Log Files": check_log_files(),
        "Google Calendar API": check_google_calendar_api(),
        "Required Scripts": check_required_scripts()
    }
    
    # Log results
    for check_name, status in checks.items():
        if status:
            logger.info(f"[OK] {check_name}: PASSED")
        else:
            logger.error(f"[ERROR] {check_name}: FAILED")
    
    logger.info("=" * 50)
    
    # Summary
    passed_checks = sum(checks.values())
    total_checks = len(checks)
    
    if passed_checks == total_checks:
        logger.info(f"[OK] HEALTH CHECK PASSED: {passed_checks}/{total_checks} checks successful")
        logger.info("System is ready for Wednesday's event synchronization runs")
    else:
        logger.error(f"[ERROR] HEALTH CHECK FAILED: {passed_checks}/{total_checks} checks successful")
        logger.error("System needs attention before Wednesday's runs")
    
    return checks

def main():
    """Main function to run the health check."""
    global logger
    logger = setup_logging()
    
    try:
        results = run_health_check()
        
        # Exit with appropriate code
        if all(results.values()):
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure
            
    except Exception as e:
        logger.error(f"Unexpected error during health check: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
