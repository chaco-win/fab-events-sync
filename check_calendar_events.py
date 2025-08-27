#!/usr/bin/env python3
"""
FAB Events Calendar Checker
Read-only script to check what events are currently in both calendars
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'sa.json'

# Calendar IDs from environment
LOCAL_CALENDAR_ID = os.getenv('LOCAL_CALENDAR_ID')
GLOBAL_CALENDAR_ID = os.getenv('CALENDAR_ID')

def setup_logging():
    """Setup logging to both console and file"""
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
    file_handler = logging.FileHandler(f'logs/check_calendar_events_{timestamp}.log')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Setup logging
logger = setup_logging()

def setup_google_calendar() -> Optional[build]:
    """Set up Google Calendar service using service account credentials"""
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            logger.error(f"Error: Service account file '{SERVICE_ACCOUNT_FILE}' not found")
            return None
        
        credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=credentials)
        
        logger.info("Successfully connected to Google Calendar API")
        return service
    
    except Exception as e:
        logger.error(f"Error setting up Google Calendar: {e}")
        return None

def get_calendar_events(service: build, calendar_id: str, calendar_name: str) -> List[Dict]:
    """Get all events from a specific calendar"""
    try:
        # Get events from the last 30 days to the next 365 days
        now = datetime.utcnow()
        start_date = (now - timedelta(days=30)).isoformat() + 'Z'
        end_date = (now + timedelta(days=365)).isoformat() + 'Z'
        
        logger.info(f"Fetching events from {calendar_name} calendar...")
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_date,
            timeMax=end_date,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        logger.info(f"Found {len(events)} total events in {calendar_name} calendar")
        return events
        
    except Exception as e:
        logger.error(f"Error fetching events from {calendar_name} calendar: {e}")
        return []

def display_calendar_events(service: build, calendar_id: str, calendar_name: str) -> int:
    """Display all events from a specific calendar"""
    if not calendar_id:
        logger.warning(f"No {calendar_name} calendar ID configured, skipping...")
        return 0
    
    logger.info(f"Checking {calendar_name} calendar...")
    
    # Get all events
    events = get_calendar_events(service, calendar_id, calendar_name)
    
    if not events:
        logger.info(f"No events found in {calendar_name} calendar")
        return 0
    
    # Display events
    logger.info(f"Events in {calendar_name} calendar:")
    logger.info("-" * 80)
    
    for i, event in enumerate(events, 1):
        summary = event.get('summary', 'Unknown Event')
        start = event.get('start', {}).get('date', 'No date')
        event_id = event.get('id', 'No ID')
        logger.info(f"{i}. {summary} ({start})")
    
    logger.info("-" * 80)
    return len(events)

def main():
    """Main function for calendar checking"""
    logger.info("=" * 80)
    logger.info("FAB Events Calendar Checker Started")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    # Check configuration
    if not LOCAL_CALENDAR_ID and not GLOBAL_CALENDAR_ID:
        logger.error("No calendar IDs configured! Check your .env file.")
        logger.error("Required variables: LOCAL_CALENDAR_ID and/or CALENDAR_ID")
        return
    
    # Set up Google Calendar service
    logger.info("Setting up Google Calendar service...")
    service = setup_google_calendar()
    
    if not service:
        logger.error("Failed to setup Google Calendar service")
        return
    
    total_events = 0
    
    # Check local calendar
    if LOCAL_CALENDAR_ID:
        local_count = display_calendar_events(service, LOCAL_CALENDAR_ID, "Local DFW")
        total_events += local_count
    else:
        logger.info("Local calendar ID not configured, skipping...")
    
    # Check global calendar
    if GLOBAL_CALENDAR_ID:
        global_count = display_calendar_events(service, GLOBAL_CALENDAR_ID, "Global Major")
        total_events += global_count
    else:
        logger.info("Global calendar ID not configured, skipping...")
    
    # Summary
    logger.info("=" * 80)
    logger.info("CALENDAR CHECK COMPLETED")
    logger.info(f"Total events found: {total_events}")
    logger.info("=" * 80)
    
    if total_events > 0:
        logger.info("📅 Calendars contain events - ready for testing!")
    else:
        logger.info("📝 No events found in calendars")

if __name__ == "__main__":
    main()
