#!/usr/bin/env python3
"""
Health Check Script for FAB Events Sync System

This script runs weekly on Tuesday to verify the system is ready
for Wednesday's event synchronization runs.

"""

import os
import sys
import logging
import requests
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

def send_discord_alert(message: str, failed_checks: List[str]) -> bool:
    """Send alert message to Discord webhook only on failures."""
    try:
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            logger.warning("No Discord webhook configured - skipping notification")
            return False
        
        # Format the failure message with details
        failed_details = "\n".join([f"❌ {check}" for check in failed_checks])
        formatted_message = f"🚨 **FAB Events Health Check FAILED**\n{message}\n\n**Failed Checks:**\n{failed_details}"
        
        data = {"content": formatted_message}
        response = requests.post(webhook_url, json=data)
        
        if response.status_code == 204:
            logger.info("Discord notification sent successfully")
            return True
        else:
            logger.error(f"Failed to send Discord notification: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to send Discord alert: {e}")
        return False

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
        # Debug: Print what we're about to import
        logger.info("DEBUG: About to import Google API modules")
        
        # Import required modules using the same pattern as working scripts
        logger.info("DEBUG: Importing google.auth.transport.requests")
        from google.auth.transport.requests import Request
        logger.info("DEBUG: Importing google.oauth2.service_account")
        from google.oauth2.service_account import Credentials as ServiceAccountCredentials
        logger.info("DEBUG: Importing googleapiclient.discovery")
        from googleapiclient.discovery import build
        
        # Debug: Check what we actually imported
        logger.info(f"DEBUG: ServiceAccountCredentials type: {type(ServiceAccountCredentials)}")
        logger.info(f"DEBUG: Has from_service_account_file: {hasattr(ServiceAccountCredentials, 'from_service_account_file')}")
        logger.info(f"DEBUG: ServiceAccountCredentials module: {ServiceAccountCredentials.__module__}")
        
        # Check if credentials file exists
        creds_file = Path("sa.json")
        if not creds_file.exists():
            logger.error("Service account credentials file not found")
            return False
        
        # Try to load credentials using the correct method
        logger.info("DEBUG: About to call from_service_account_file")
        creds = ServiceAccountCredentials.from_service_account_file("sa.json")
        logger.info("DEBUG: Credentials loaded successfully")
        
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                logger.error("Invalid or expired credentials")
                return False
        
        # Try to build the service
        logger.info("DEBUG: About to build calendar service")
        service = build('calendar', 'v3', credentials=creds)
        
        # Simple API call to test connectivity
        logger.info("DEBUG: About to test API call")
        calendar_list = service.calendarList().list(maxResults=1).execute()
        
        logger.info("Google Calendar API is accessible")
        return True
        
    except ImportError as e:
        logger.error(f"Required Google API modules not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Error testing Google Calendar API: {e}")
        logger.error(f"DEBUG: Exception type: {type(e)}")
        logger.error(f"DEBUG: Exception details: {str(e)}")
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
        success_message = f"System is ready for Wednesday's event synchronization runs ({passed_checks}/{total_checks} checks successful)"
        logger.info(f"[OK] HEALTH CHECK PASSED: {passed_checks}/{total_checks} checks successful")
        logger.info("System is ready for Wednesday's event synchronization runs")
        
        # No Discord notification on success - only on failures
        logger.info("All checks passed - no Discord notification needed")
    else:
        failure_message = f"System needs attention before Wednesday's runs ({passed_checks}/{total_checks} checks successful)"
        logger.error(f"[ERROR] HEALTH CHECK FAILED: {passed_checks}/{total_checks} checks successful")
        logger.error("System needs attention before Wednesday's runs")
        
        # Get list of failed checks for detailed Discord message
        failed_checks = [check_name for check_name, status in checks.items() if not status]
        
        # Send Discord failure notification with details
        send_discord_alert(failure_message, failed_checks)
    
    return checks

def main():
    """Main function to run the health check."""
    global logger
    
    # Debug output to help troubleshoot
    print("DEBUG: Starting health check script")
    print(f"DEBUG: Current working directory: {os.getcwd()}")
    print(f"DEBUG: Python executable: {sys.executable}")
    print(f"DEBUG: Python version: {sys.version}")
    
    try:
        logger = setup_logging()
        print("DEBUG: Logging setup completed")
        
        results = run_health_check()
        print(f"DEBUG: Health check results: {results}")
        
        # Exit with appropriate code
        if all(results.values()):
            print("DEBUG: All checks passed, exiting with code 0")
            sys.exit(0)  # Success
        else:
            print("DEBUG: Some checks failed, exiting with code 1")
            sys.exit(1)  # Failure
            
    except Exception as e:
        error_message = f"Unexpected error during health check: {e}"
        print(f"DEBUG: Exception occurred: {e}")
        
        # Try to set up logging if it failed earlier
        if 'logger' not in globals():
            try:
                logger = setup_logging()
            except:
                # If logging setup fails, just print to console
                print(f"ERROR: {error_message}")
                sys.exit(1)
        
        logger.error(error_message)
        
        # Send Discord error notification
        send_discord_alert(error_message, ["Unexpected System Error"])
        
        sys.exit(1)

if __name__ == "__main__":
    main()
