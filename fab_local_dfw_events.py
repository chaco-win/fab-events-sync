#!/usr/bin/env python3
"""
FAB Local Events Scraper - Clean API-Ready Version
Fetches competitive event types with dynamic filter discovery
"""

import requests
import re
import json
import time
import logging
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import hashlib

# Load env: base .env then override with .env.local if present
load_dotenv(dotenv_path='.env', override=False)
if os.path.exists('.env.local'):
    load_dotenv(dotenv_path='.env.local', override=True)

# Configuration constants
EVENTS_API_URL = os.getenv('FAB_LOCAL_API_URL', 'https://gem.fabtcg.com/api/v1/locator/events/')
API_LANGUAGE = os.getenv('FAB_API_LANGUAGE', 'en-US')
SEARCH_LOCATION = os.getenv('SEARCH_LOCATION', 'Fort Worth, TX 76117, USA')
MAX_DISTANCE_COMPETITIVE = int(os.getenv('MAX_DISTANCE_COMPETITIVE', '250'))
MAX_DISTANCE_PRERELEASE = int(os.getenv('MAX_DISTANCE_PRERELEASE', '100'))
REQUEST_DELAY = int(os.getenv('REQUEST_DELAY', '1'))  # seconds between requests
DISTANCE_UNIT = os.getenv('DISTANCE_UNIT', 'mi').lower()
if DISTANCE_UNIT not in ('mi', 'km'):
    DISTANCE_UNIT = 'mi'

DISTANCE_CONVERSION = 1.609344  # miles <-> km

TARGET_EVENT_TYPE_MATCHERS: List[Tuple[str, List[str]]] = [
    ('Pro Quest+', ['pro quest+']),
    ('Pro Quest', ['pro quest']),
    ('Skirmish', ['skirmish']),
    ('Road to Nationals', ['road to nationals']),
    ('Prerelease', ['prerelease', 'pre-release', 'pre release']),
]

# Google Calendar Configuration
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'sa.json'
LOCAL_CALENDAR_ID = os.getenv('LOCAL_CALENDAR_ID')  # Your new local events calendar ID

# Configure logging to both console and file
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
    file_handler = logging.FileHandler(f'logs/fab_local_dfw_events_{timestamp}.log')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Setup logging
logger = setup_logging()

# Log script start
logger.info("=" * 80)
logger.info("FAB Local DFW Events Scraper Started")
logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"Events API URL: {EVENTS_API_URL}")
logger.info(f"Search Location: {SEARCH_LOCATION}")
logger.info(f"Max Distance (Competitive): {MAX_DISTANCE_COMPETITIVE} {DISTANCE_UNIT}")
logger.info(f"Max Distance (Prerelease): {MAX_DISTANCE_PRERELEASE} {DISTANCE_UNIT}")
logger.info("=" * 80)

def fetch_events_api(params: Dict) -> Optional[Dict]:
    """Fetch event data from the FAB locator API."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': API_LANGUAGE
        }
        response = requests.get(EVENTS_API_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Network error fetching events: {e}")
        return None
    except ValueError as e:
        logger.error(f"Invalid JSON from events API: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching events: {e}")
        return None

def miles_to_km(miles: float) -> float:
    return miles * DISTANCE_CONVERSION

def km_to_miles(km: float) -> float:
    return km / DISTANCE_CONVERSION

def normalize_distance_for_api(distance: int) -> int:
    """Convert configured distance to API distance (km)."""
    if DISTANCE_UNIT == 'km':
        return distance
    return int(round(miles_to_km(distance)))

def normalize_distance_value(distance: Optional[float], unit: Optional[str]) -> Tuple[Optional[float], str]:
    """Normalize API distance into configured units for display/filtering."""
    if distance is None:
        return None, DISTANCE_UNIT
    unit = (unit or 'km').lower()
    if DISTANCE_UNIT == unit:
        return distance, unit
    if DISTANCE_UNIT == 'mi' and unit == 'km':
        return km_to_miles(distance), 'mi'
    if DISTANCE_UNIT == 'km' and unit == 'mi':
        return miles_to_km(distance), 'km'
    return distance, unit

def format_day_suffix(day: int) -> str:
    if 11 <= day <= 13:
        return "th"
    if day % 10 == 1:
        return "st"
    if day % 10 == 2:
        return "nd"
    if day % 10 == 3:
        return "rd"
    return "th"

def format_date_text(dt: datetime) -> str:
    day_name = dt.strftime('%a')
    month = dt.strftime('%b')
    suffix = format_day_suffix(dt.day)
    return f"{day_name} {dt.day}{suffix} {month}"

def format_time_text(dt: datetime) -> str:
    return dt.strftime('%I:%M %p').lstrip('0')

def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None

def build_event_type_map(event_types: List[Dict]) -> Dict[int, str]:
    """Map event type IDs to canonical labels."""
    type_map: Dict[int, str] = {}
    for event_type in event_types:
        title = (event_type.get('title') or '').strip()
        if not title:
            continue
        title_lower = title.lower()
        for label, patterns in TARGET_EVENT_TYPE_MATCHERS:
            if any(pat in title_lower for pat in patterns):
                type_id = event_type.get('id')
                if isinstance(type_id, int):
                    type_map[type_id] = label
                break
    return type_map

def fetch_event_type_filters() -> List[Dict]:
    """Fetch available event type filters from the API."""
    data = fetch_events_api({'mode': 'event', 'page': 1})
    if not data:
        return []
    filters = data.get('filters') or {}
    return filters.get('event_types') or []

def fetch_events_for_type(type_id: int, search: str, distance: int) -> List[Dict]:
    """Fetch all events for a given event type with paging."""
    events: List[Dict] = []
    page = 1
    while True:
        params: Dict[str, object] = {'mode': 'event', 'page': page}
        if search:
            params['search'] = search
        if distance:
            params['distance'] = distance
        if type_id:
            params['type'] = type_id
        data = fetch_events_api(params)
        if not data:
            break
        results = data.get('results') or []
        events.extend(results)
        if not data.get('next'):
            break
        page += 1
        time.sleep(REQUEST_DELAY)
    return events

def build_event_data(item: Dict, event_type: str) -> Dict:
    """Normalize API event data to the local event schema."""
    store_name = item.get('organiser_name') or item.get('nickname') or "Unknown Store"
    start_dt = parse_iso_datetime(item.get('start_time'))
    date_text = format_date_text(start_dt) if start_dt else ''
    time_text = format_time_text(start_dt) if start_dt else ''

    distance_value, distance_unit = normalize_distance_value(item.get('distance'), item.get('distance_unit'))
    if distance_value is not None:
        distance_value = round(distance_value, 2)

    event_data = {
        'event_id': item.get('id'),
        'event_type': event_type,
        'store_name': store_name,
        'title': f"{event_type}: {store_name}",
        'date_text': date_text,
        'time': time_text,
        'format': item.get('format_name'),
        'location': item.get('address'),
        'distance': str(distance_value) if distance_value is not None else '0',
        'distance_unit': distance_unit,
        'url': item.get('event_link'),
        'start_time': item.get('start_time')
    }

    return event_data

def scrape_specific_event_types():
    """Fetch competitive events using the locator API."""
    event_type_filters = fetch_event_type_filters()
    if not event_type_filters:
        return []

    type_map = build_event_type_map(event_type_filters)
    if not type_map:
        logger.warning("No matching competitive event types found in API filters.")
        return []

    all_events: List[Dict] = []
    for type_id, category in type_map.items():
        max_distance = MAX_DISTANCE_PRERELEASE if category == 'Prerelease' else MAX_DISTANCE_COMPETITIVE
        distance = normalize_distance_for_api(max_distance)
        results = fetch_events_for_type(type_id, SEARCH_LOCATION, distance)
        for item in results:
            all_events.append(build_event_data(item, category))

    # Remove duplicates based on API event ID
    unique_events = []
    seen_events = set()
    for event in all_events:
        event_id = event.get('event_id')
        event_key = event_id if event_id is not None else f"{event.get('store_name', '')}_{event.get('date_text', '')}_{event.get('event_type', '')}"
        if event_key not in seen_events:
            seen_events.add(event_key)
            unique_events.append(event)

    return unique_events

def filter_events_by_distance(events):
    """Filter events by distance (Prerelease: 100 miles, others: 250 miles)"""
    filtered_events = []
    
    for event in events:
        try:
            distance = float(event.get('distance', '0'))
            event_type = event.get('event_type', '')
            
            # Apply distance limits based on event type
            max_distance = MAX_DISTANCE_PRERELEASE if event_type == 'Prerelease' else MAX_DISTANCE_COMPETITIVE
            if distance <= max_distance:
                filtered_events.append(event)
        except (ValueError, TypeError):
            # If distance parsing fails, include the event (distance filtering will be skipped)
            filtered_events.append(event)
    
    return filtered_events

def display_results(events):
    """Display results in a clean format"""
    if not events:
        print("No competitive events found!")
        return
    
    # Group events by type
    events_by_type = {}
    for event in events:
        event_type = event.get('event_type', 'Unknown')
        events_by_type.setdefault(event_type, []).append(event)
    
    # Display organized by type
    for event_type in sorted(events_by_type.keys()):
        type_events = events_by_type[event_type]
        print(f"{event_type.upper()}: {len(type_events)} events")
        
        for event in type_events:
            format_info = f" ({event.get('format', 'Unknown')})" if event.get('format') else ""
            print(f"  {event.get('store_name', 'Unknown Store')} - {event.get('date_text', 'Unknown')} {event.get('time', '')}{format_info}")

def get_competitive_events():
    """API-ready function to get all competitive events"""
    events = scrape_specific_event_types()
    if not events:
        return []
    
    # Filter by distance
    filtered_events = filter_events_by_distance(events)
    return filtered_events

def get_competitive_events_by_type(event_type=None):
    """Get events filtered by specific type (optional)"""
    events = get_competitive_events()
    if event_type:
        events = [e for e in events if e.get('event_type', '').lower() == event_type.lower()]
    return events

def setup_google_calendar():
    """Set up Google Calendar service"""
    try:
        if not LOCAL_CALENDAR_ID:
            logger.error("LOCAL_CALENDAR_ID not found in environment variables")
            return None
            
        credentials = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=credentials)
        
        # Test connection
        calendar = service.calendars().get(calendarId=LOCAL_CALENDAR_ID).execute()
        logger.info(f"Connected to Google Calendar: {calendar['summary']}")
        return service
        
    except Exception as e:
        logger.error(f"Failed to setup Google Calendar: {e}")
        return None

def parse_local_event_date(date_text, start_time: Optional[str] = None):
    """Parse local event date format (e.g., 'Sat 4th Oct') or ISO start_time to datetime."""
    try:
        if start_time:
            iso_dt = parse_iso_datetime(start_time)
            if iso_dt:
                return iso_dt

        # Handle formats like "Sat 4th Oct", "Sun 21st Sep"
        date_pattern = r'([A-Za-z]{3})\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,4})'
        match = re.search(date_pattern, date_text)
        
        if match:
            day_name, day_num, month = match.groups()
            day_num = int(day_num)
            
            # Map month abbreviations to numbers
            month_map = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }
            
            month_num = month_map.get(month, 1)
            current_year = datetime.now().year
            
            # Create datetime object
            event_date = datetime(current_year, month_num, day_num)
            
            # If the date is in the past, assume next year
            if event_date < datetime.now():
                event_date = datetime(current_year + 1, month_num, day_num)
            
            return event_date
            
    except Exception as e:
        logger.error(f"Error parsing date '{date_text}': {e}")
    
    return None

def create_calendar_event(service, event):
    """Create a Google Calendar event from local event data"""
    try:
        # Parse the date
        event_date = parse_local_event_date(event.get('date_text', ''), event.get('start_time'))
        if not event_date:
            logger.warning(f"Could not parse date for {event.get('title', 'Unknown')}")
            return None
        
        # Create full-day event (no specific time)
        start_date = event_date
        end_date = event_date + timedelta(days=1)  # End at start of next day
        
        # Create event description with time and format
        description_parts = []
        if event.get('time'):
            description_parts.append(f"Time: {event['time']}")
        if event.get('format'):
            description_parts.append(f"Format: {event['format']}")
        if event.get('location'):
            description_parts.append(f"Address: {event['location']}")
        if event.get('distance'):
            description_parts.append(f"Distance: {event['distance']} {event.get('distance_unit', 'mi')}")
        
        description = "\n".join(description_parts) if description_parts else "Local FAB Event"
        
        # Create calendar event as full-day event (matching global events script)
        calendar_event = {
            'summary': event.get('title', 'FAB Local Event'),
            'location': event.get('location', ''),
            'description': description,
            'start': {
                'date': start_date.strftime('%Y-%m-%d'),
                'timeZone': 'America/Chicago',  # DFW timezone
            },
            'end': {
                'date': end_date.strftime('%Y-%m-%d'),
                'timeZone': 'America/Chicago',
            },
            'colorId': get_event_color(event.get('event_type', ''))
        }
        
        return calendar_event
        
    except Exception as e:
        logger.error(f"Error creating calendar event for {event.get('title', 'Unknown')}: {e}")
        return None

def get_event_color(event_type):
    """Get Google Calendar color ID for event type - using soft, easy-on-the-eyes colors"""
    color_map = {
        'Pro Quest': '8',      # Soft Lavender (different from major events blue)
        'Pro Quest+': '8',     # Soft Lavender
        'Skirmish': '9',       # Soft Sage Green (different from major events orange)
        'Road to Nationals': '10', # Soft Peach (different from major events green)
        'Prerelease': '11',    # Soft Blue (different from major events red)
        'Pre-Release': '11',   # Soft Blue
        'Pre Release': '11'    # Soft Blue
    }
    return color_map.get(event_type, '1')  # Default to gray

def sync_events_to_calendar(service, events):
    """Sync local events to Google Calendar"""
    if not service:
        logger.error("No Google Calendar service available")
        return
    
    logger.info(f"Syncing {len(events)} local events to Google Calendar...")
    
    success_count = 0
    for event in events:
        calendar_event = create_calendar_event(service, event)
        if calendar_event:
            try:
                # Check if event already exists
                existing_events = service.events().list(
                    calendarId=LOCAL_CALENDAR_ID,
                    q=event.get('title', ''),
                    timeMin=calendar_event['start']['date'] + 'T00:00:00Z',
                    timeMax=calendar_event['end']['date'] + 'T00:00:00Z'
                ).execute()
                
                if existing_events['items']:
                    # Update existing event
                    event_id = existing_events['items'][0]['id']
                    updated_event = service.events().update(
                        calendarId=LOCAL_CALENDAR_ID,
                        eventId=event_id,
                        body=calendar_event
                    ).execute()
                    logger.info(f"  [UPDATED] {event.get('title', 'Unknown')}")
                else:
                    # Create new event
                    created_event = service.events().insert(
                        calendarId=LOCAL_CALENDAR_ID,
                        body=calendar_event
                    ).execute()
                    logger.info(f"  [CREATED] {event.get('title', 'Unknown')}")
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"  ❌ ERROR: {event.get('title', 'Unknown')} - {e}")
    
    logger.info(f"Successfully synced {success_count} local events to calendar")

def health_check() -> Dict:
    """API health check function"""
    try:
        # Test basic functionality
        events = get_competitive_events()
        calendar_service = setup_google_calendar()
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "event_count": len(events),
            "event_types": list(set(e.get('event_type', '') for e in events)),
            "calendar_connected": calendar_service is not None,
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e),
            "version": "1.0.0"
        }

def main():
    """Main function for testing"""
    logger.info("Starting FAB Local DFW Events Scraper & Calendar Sync")
    logger.info("=" * 60)
    
    # Get events
    logger.info("Fetching competitive events...")
    events = get_competitive_events()
    
    if not events:
        logger.warning("No competitive events found!")
        return
    
    # Display results
    display_results(events)

    # Write API-ready JSON for the Discord bot
    try:
        os.makedirs('data', exist_ok=True)
        records = []
        now_iso = datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
        for e in events:
            base = f"{LOCAL_CALENDAR_ID}:{e.get('title','')}:{e.get('location','') or e.get('store_name','')}:{e.get('date_text','')}"
            event_id = hashlib.sha1(base.encode('utf-8')).hexdigest()
            # Parse start date using the local parser
            try:
                start_dt = parse_local_event_date(e.get('date_text', '') or '', e.get('start_time'))
            except Exception:
                start_dt = None
            starts_at = (start_dt or datetime.utcnow()).strftime('%Y-%m-%dT00:00:00Z')
            records.append({
                'event_id': event_id,
                'calendar_id': str(LOCAL_CALENDAR_ID) if LOCAL_CALENDAR_ID else 'local',
                'title': e.get('title', ''),
                'starts_at': starts_at,
                'ends_at': None,
                'url': e.get('url') or None,
                'updated_at': now_iso,
                'location': e.get('location') or e.get('store_name') or None,
            })
        out_path = os.path.join('data', 'dfw_events.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        logger.info(f"Wrote {len(records)} events to {out_path}")
    except Exception as write_err:
        logger.error(f"Failed to write JSON to data/: {write_err}")
    
    logger.info(f"Scraping complete! Found {len(events)} competitive events.")
    
    # Set up Google Calendar
    logger.info("Setting up Google Calendar...")
    service = setup_google_calendar()
    
    if service:
        # Sync to calendar
        sync_events_to_calendar(service, events)
        logger.info("Calendar sync completed!")
    else:
        logger.warning("Calendar sync skipped - check LOCAL_CALENDAR_ID in .env file")
    
    logger.info("Script execution completed successfully")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
