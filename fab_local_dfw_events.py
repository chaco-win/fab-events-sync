#!/usr/bin/env python3
"""
FAB Local Events Scraper - Clean API-Ready Version
Fetches competitive event types with dynamic filter discovery
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import logging
import os
from typing import List, Dict, Optional
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
BASE_URL = os.getenv('FAB_LOCAL_URL', 'https://fabtcg.com/en/events/')
SEARCH_LOCATION = os.getenv('SEARCH_LOCATION', 'Fort Worth, TX 76117, USA')
MAX_DISTANCE_COMPETITIVE = int(os.getenv('MAX_DISTANCE_COMPETITIVE', '250'))
MAX_DISTANCE_PRERELEASE = int(os.getenv('MAX_DISTANCE_PRERELEASE', '100'))
REQUEST_DELAY = int(os.getenv('REQUEST_DELAY', '1'))  # seconds between requests

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
logger.info(f"Base URL: {BASE_URL}")
logger.info(f"Search Location: {SEARCH_LOCATION}")
logger.info(f"Max Distance (Competitive): {MAX_DISTANCE_COMPETITIVE} miles")
logger.info(f"Max Distance (Prerelease): {MAX_DISTANCE_PRERELEASE} miles")
logger.info("=" * 80)

def fetch_page(url: str, params: Optional[Dict] = None) -> Optional[str]:
    """Fetch a web page with query parameters"""
    try:
        if params:
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            full_url = f"{url}?{query_string}"
        else:
            full_url = url
            
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(full_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"Network error fetching {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}")
        return None

def find_events_on_page(html, event_type):
    """Find events on a page for a specific event type"""
    events = []
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find all h2 elements (event titles)
    h2_elements = soup.find_all('h2')
    
    # Pre-compile regex patterns for efficiency
    distance_pattern = re.compile(r'\(([\d.]+)\s*(mi|km)\)')
    date_pattern = re.compile(r'([A-Za-z]{3})\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,4})')
    time_patterns = [
        re.compile(r'(\d{1,2}:\d{2}\s*[AP]M)'),
        re.compile(r'(\d{1,2}\s*[AP]M)')
    ]
    address_pattern = re.compile(r'([A-Za-z\s,]+,\s*[A-Z]{2}\s*\d{5})')
    
    # Event type patterns for store name extraction - more flexible
    event_type_patterns = [
        r'skirmish season \d+',           # "Skirmish Season 12" (any season)
        r'pro quest [a-z\s]+',           # "Pro Quest Yokohama", "Pro Quest San Marcos", etc.
        r'pro quest\+',                   # "Pro Quest+"
        r'[a-z\s]+ pre-release',         # "Super Slam Pre-Release", "High Seas Pre-Release", etc.
        r'pro quest',                     # Generic "Pro Quest"
        r'road to nationals',             # "Road to Nationals"
        r'prerelease',                    # Generic "Prerelease"
        r'pre-release'                    # Alternative spelling
    ]
    
    # Format patterns
    format_patterns = ['Classic Constructed', 'Blitz', 'Living Legend', 'Commoner', 'Booster Draft', 'Sealed Deck', 'Crack, Shuffle, Play!', 'Ira - Learn to Play']
    
    for h2 in h2_elements:
        h2_text = h2.get_text().strip()
        if not h2_text:
            continue
        
        # Skip non-event H2 elements
        if any(skip_text in h2_text.lower() for skip_text in ['no results found', 'no events found', 'no matches found']):
            continue
        
        # Get the parent container
        container = h2.parent
        container_text = container.get_text()
        
        # Extract store name - improved logic
        clean_text = distance_pattern.sub('', h2_text).strip()
        
        # For Pro Quest events, we need to handle the city name properly
        if 'pro quest' in clean_text.lower():
            # Look for the pattern "Pro Quest [City] [Store Name]"
            # We want to remove "Pro Quest [City]" but keep the store name
            pro_quest_match = re.search(r'pro quest\s+([a-z\s]+?)(?:\s+([a-z\s&\'-]+))?$', clean_text.lower())
            if pro_quest_match:
                city = pro_quest_match.group(1).strip()
                store_part = pro_quest_match.group(2) if pro_quest_match.group(2) else ""
                
                # Remove "Pro Quest [City]" from the original text
                pattern_to_remove = f"Pro Quest {city}"
                store_name = re.sub(pattern_to_remove, '', clean_text, flags=re.IGNORECASE).strip()
                
                # If we still have the city name, remove it too
                if city in store_name:
                    store_name = re.sub(city, '', store_name, flags=re.IGNORECASE).strip()
                
                # Clean up extra whitespace and newlines
                store_name = re.sub(r'\s+', ' ', store_name).strip()
            else:
                # Fallback: just remove "Pro Quest" and clean up
                store_name = re.sub(r'pro quest', '', clean_text, flags=re.IGNORECASE).strip()
                store_name = re.sub(r'\s+', ' ', store_name).strip()
        else:
            # For other event types, use the original logic
            original_clean_text = clean_text
            for pattern in event_type_patterns:
                if re.match(pattern, clean_text.lower()):
                    clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE).strip()
                    break
            
            if not clean_text or len(clean_text) < 3:
                for pattern in event_type_patterns:
                    if re.search(pattern, original_clean_text.lower()):
                        match = re.search(pattern, original_clean_text.lower())
                        if match:
                            end_pos = match.end()
                            store_name = original_clean_text[end_pos:].strip()
                            if store_name and len(store_name) > 2:
                                break
                        else:
                            store_name = "Unknown Store"
                    else:
                        store_name = original_clean_text.strip()
            else:
                store_name = clean_text
        
        # Final cleanup
        if not store_name or len(store_name) < 3:
            store_name = "Unknown Store"
        
        # Clean up any remaining whitespace issues
        store_name = re.sub(r'\s+', ' ', store_name).strip()
        
        # Create event data
        event_data = {
            'event_type': event_type,
            'store_name': store_name,
            'title': f"{event_type}: {store_name}"
        }
        
        # Extract date and time from P tag (preferred) or container
        source_text = container.find('p').get_text() if container.find('p') else container_text
        
        # Date
        date_match = date_pattern.search(source_text)
        if date_match:
            day_name, day_num, month = date_match.groups()
            # Fix date suffixes (1st, 2nd, 3rd, 4th, etc.)
            day_num = int(day_num)
            if day_num == 1:
                suffix = "st"
            elif day_num == 2:
                suffix = "nd"
            elif day_num == 3:
                suffix = "rd"
            elif day_num == 21:
                suffix = "st"
            elif day_num == 22:
                suffix = "nd"
            elif day_num == 23:
                suffix = "rd"
            elif day_num == 31:
                suffix = "st"
            else:
                suffix = "th"
            event_data['date_text'] = f"{day_name} {day_num}{suffix} {month}"
        
        # Time
        for time_pattern in time_patterns:
            time_match = time_pattern.search(source_text)
            if time_match:
                event_data['time'] = time_match.group(1)
                break
        
        # Format
        for format_name in format_patterns:
            if format_name in container_text:
                event_data['format'] = format_name
                break
        
        # Location
        address_match = address_pattern.search(container_text)
        if address_match:
            event_data['location'] = address_match.group(1).strip()
        
        # Distance
        distance_match = distance_pattern.search(container_text)
        if distance_match and len(distance_match.groups()) >= 2:
            try:
                event_data['distance'] = distance_match.group(1)
                event_data['distance_unit'] = distance_match.group(2)
            except IndexError:
                # Fallback if groups are missing
                event_data['distance'] = '0'
                event_data['distance_unit'] = 'mi'
        else:
            # Default values if no distance found
            event_data['distance'] = '0'
            event_data['distance_unit'] = 'mi'
        
        events.append(event_data)
    
    return events

def get_total_pages(html):
    """Get total number of pages from pagination"""
    soup = BeautifulSoup(html, 'html.parser')
    pagination = soup.find(class_=re.compile(r'pagination|pages'))
    if not pagination:
        return 1
    
    page_numbers = pagination.find_all(['a', 'span'])
    if not page_numbers:
        return 1
    
    # Find the highest page number
    max_page = 1
    for page_elem in page_numbers:
        page_text = page_elem.get_text().strip()
        if page_text.isdigit():
            max_page = max(max_page, int(page_text))
    
    return max_page

def discover_event_type_filters(html):
    """Discover available event type filter options from dropdown"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find event type dropdown
    event_type_dropdown = soup.find('select', {'name': 'type'}) or soup.find('select', {'id': 'type'})
    if not event_type_dropdown:
        return {}
    
    # Extract options
    event_types = {}
    for option in event_type_dropdown.find_all('option'):
        value = option.get('value', '').strip()
        text = option.get_text().strip()
        if value and text:
            event_types[text] = value
    
    return event_types

def scrape_specific_event_types():
    """Scrape specific competitive event types using discovered filter values"""
    # Discover available filters
    main_html = fetch_page(BASE_URL)
    if not main_html:
        return []
    
    event_type_filters = discover_event_type_filters(main_html)
    
    # Target event types and their search terms - more flexible
    target_types = {
        'Pro Quest': ['Pro Quest', 'Pro Quest+'],
        'Skirmish': ['Skirmish'],
        'Road to Nationals': ['Road to Nationals'],
        'Prerelease': ['Prerelease', 'Pre-Release', 'Pre Release']
    }
    
    # Base search parameters
    base_params = {
        'distance': str(MAX_DISTANCE_COMPETITIVE),
        'query': SEARCH_LOCATION
    }
    
    all_events = []
    
    # Scrape each target type
    for category, search_terms in target_types.items():
        # Find matching filters
        matching_filters = [
            (filter_name, filter_value) 
            for filter_name, filter_value in event_type_filters.items()
            if any(search_term.lower() in filter_name.lower() for search_term in search_terms)
        ]
        
        if not matching_filters:
            continue
        
        # Scrape each matching filter
        for filter_name, filter_value in matching_filters:
            params = base_params.copy()
            params['type'] = filter_value
            
            # Scrape all pages for this filter
            page = 1
            while True:
                page_params = params.copy()
                page_params['page'] = page
                
                html = fetch_page(BASE_URL, page_params)
                if not html:
                    break
                
                # Get total pages on first page
                if page == 1:
                    total_pages = get_total_pages(html)
                
                # Extract events from this page
                page_events = find_events_on_page(html, category)
                all_events.extend(page_events)
                
                if page >= total_pages:
                    break
                
                page += 1
                time.sleep(REQUEST_DELAY)  # Be nice to the server
    
    # Remove duplicates based on store name and date
    unique_events = []
    seen_events = set()
    
    for event in all_events:
        # Create a unique key for each event
        event_key = f"{event.get('store_name', '')}_{event.get('date_text', '')}_{event.get('event_type', '')}"
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

def parse_local_event_date(date_text):
    """Parse local event date format (e.g., 'Sat 4th Oct') to datetime"""
    try:
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
        event_date = parse_local_event_date(event.get('date_text', ''))
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
                start_dt = parse_local_event_date(e.get('date_text', '') or '')
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
