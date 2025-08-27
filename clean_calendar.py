#!/usr/bin/env python3
"""
FAB Events Calendar Cleaner
Cleans both local and global FAB event calendars for testing purposes
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
    file_handler = logging.FileHandler(f'logs/clean_calendar_{timestamp}.log')
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

def get_events_to_clean(service: build, calendar_id: str, calendar_name: str) -> List[Dict]:
    """Get events to clean from a specific calendar (all events for local, FAB events for global)"""
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
        
        # For local calendar, get ALL events (since they might not have FAB keywords)
        # For global calendar, filter for FAB events only
        if 'Local' in calendar_name:
            logger.info(f"Found {len(events)} total events in {calendar_name} calendar")
            return events
        else:
            # Filter for FAB events only in global calendar
            fab_events = []
            for event in events:
                summary = event.get('summary', '')
                description = event.get('description', '')
                
                # Check if this is a FAB event
                if any(keyword in summary.lower() for keyword in ['fab', 'flesh and blood', 'battle hardened', 'calling', 'world championship', 'pro tour', 'world premiere']):
                    fab_events.append(event)
                elif any(keyword in description.lower() for keyword in ['fab', 'flesh and blood', 'battle hardened', 'calling', 'world championship', 'pro tour', 'world premiere']):
                    fab_events.append(event)
            
            logger.info(f"Found {len(fab_events)} FAB events in {calendar_name} calendar")
            return fab_events
        
    except Exception as e:
        logger.error(f"Error fetching events from {calendar_name} calendar: {e}")
        return []

def delete_event(service: build, calendar_id: str, event_id: str, event_summary: str, calendar_name: str) -> bool:
    """Delete a specific event from a calendar"""
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        logger.info(f"  [OK] DELETED: {event_summary}")
        return True
    except Exception as e:
        logger.error(f"  [ERROR] deleting {event_summary}: {e}")
        return False

def clean_calendar(service: build, calendar_id: str, calendar_name: str) -> int:
    """Clean all FAB events from a specific calendar"""
    if not calendar_id:
        logger.warning(f"No {calendar_name} calendar ID configured, skipping...")
        return 0
    
    logger.info(f"Cleaning {calendar_name} calendar...")
    
    # Get events to clean (all for local, FAB events for global)
    events = get_events_to_clean(service, calendar_id, calendar_name)
    
    if not events:
        logger.info(f"No events found in {calendar_name} calendar")
        return 0
    
    # Display events that will be deleted
    if 'Local' in calendar_name:
        logger.info(f"ALL events to be deleted from {calendar_name} calendar:")
    else:
        logger.info(f"FAB events to be deleted from {calendar_name} calendar:")
    logger.info("-" * 80)
    
    for i, event in enumerate(events, 1):
        summary = event.get('summary', 'Unknown Event')
        start = event.get('start', {}).get('date', 'No date')
        event_id = event.get('id', 'No ID')
        logger.info(f"{i}. {summary} ({start})")
    
    logger.info("-" * 80)
    
    # Confirm deletion
    if 'Local' in calendar_name:
        confirm = input(f"\nAre you sure you want to delete ALL {len(events)} events from {calendar_name} calendar? (yes/no): ")
    else:
        confirm = input(f"\nAre you sure you want to delete {len(events)} FAB events from {calendar_name} calendar? (yes/no): ")
    
    if confirm.lower() != 'yes':
        logger.info(f"Deletion cancelled for {calendar_name} calendar")
        return 0
    
    # Delete events
    deleted_count = 0
    for event in events:
        event_id = event.get('id')
        summary = event.get('summary', 'Unknown Event')
        
        if event_id:
            if delete_event(service, calendar_id, event_id, summary, calendar_name):
                deleted_count += 1
    
    logger.info(f"Successfully deleted {deleted_count} events from {calendar_name} calendar")
    return deleted_count

def main():
    """Main function for calendar cleaning"""
    logger.info("=" * 80)
    logger.info("FAB Events Calendar Cleaner Started")
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
    
    total_deleted = 0
    
    # Clean local calendar
    if LOCAL_CALENDAR_ID:
        deleted_local = clean_calendar(service, LOCAL_CALENDAR_ID, "Local DFW")
        total_deleted += deleted_local
    else:
        logger.info("Local calendar ID not configured, skipping...")
    
    # Clean global calendar
    if GLOBAL_CALENDAR_ID:
        deleted_global = clean_calendar(service, GLOBAL_CALENDAR_ID, "Global Major")
        total_deleted += deleted_global
    else:
        logger.info("Global calendar ID not configured, skipping...")
    
    # Summary
    logger.info("=" * 80)
    logger.info("CALENDAR CLEANING COMPLETED")
    logger.info(f"Total events deleted: {total_deleted}")
    logger.info("=" * 80)
    
    if total_deleted > 0:
        logger.info("🎉 Calendars are now clean and ready for testing!")
    else:
        logger.info("📝 No events were deleted - calendars may already be clean")

if __name__ == "__main__":
    main()
