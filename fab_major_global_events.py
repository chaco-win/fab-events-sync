#!/usr/bin/env python3
"""
FAB Events Calendar Sync - Final Version
Combines working parsing logic with Google Calendar API integration
"""

# Standard library imports
import os
import re
import json
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# Third-party imports
import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration constants
FAB_GLOBAL_URL = os.getenv('FAB_GLOBAL_URL', 'https://fabtcg.com/en/organised-play/')
FAB_LOCAL_URL = os.getenv('FAB_LOCAL_URL', 'https://fabtcg.com/en/events/')

# Google Calendar Configuration
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'sa.json'
CALENDAR_ID = os.getenv('CALENDAR_ID')  # Set this environment variable

# Event filtering configuration
INCLUDE_GLOBAL_MAJORS = os.getenv('INCLUDE_GLOBAL_MAJORS', 'true').lower() == 'true'
INCLUDE_US_BATTLE_HARDENED = os.getenv('INCLUDE_US_BATTLE_HARDENED', 'true').lower() == 'true'
LOCAL_RADIUS_MILES = int(os.getenv('LOCAL_RADIUS_MILES', '100'))  # miles
USER_LOCATION = os.getenv('USER_LOCATION', 'Seattle, WA')  # Adjust to your location

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
    file_handler = logging.FileHandler(f'logs/fab_major_global_events_{timestamp}.log')
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
logger.info("FAB Major Global Events Scraper Started")
logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"Global URL: {FAB_GLOBAL_URL}")
logger.info(f"Local URL: {FAB_LOCAL_URL}")
logger.info(f"Calendar ID: {CALENDAR_ID}")
logger.info(f"User Location: {USER_LOCATION}")
logger.info(f"Local Radius: {LOCAL_RADIUS_MILES} miles")
logger.info(f"Include Global Majors: {INCLUDE_GLOBAL_MAJORS}")
logger.info(f"Include US Battle Hardened: {INCLUDE_US_BATTLE_HARDENED}")
logger.info("=" * 80)

def fetch_page(url: str) -> Optional[str]:
    """Fetch a web page"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"Network error fetching {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}")
        return None

def find_date_in_text(text: str) -> Optional[str]:
    """Find date patterns in text using regex patterns"""
    date_patterns = [
        # Single month patterns
        r'([A-Za-z]{3}\s+\d{1,2}-\d{1,2},?\s+\d{4})',  # Aug 15-17, 2025
        r'([A-Za-z]{3}\s+\d{1,2}-\d{1,2}\s+\d{4})',   # Aug 15-17 2025
        r'([A-Za-z]{3}\s+\d{1,2}\s*-\s*\d{1,2},?\s+\d{4})',  # Aug 15 - 17, 2025
        r'([A-Za-z]{3}\s+\d{1,2}\s*-\s*\d{1,2}\s+\d{4})',    # Aug 15 - 17 2025
        
        # Cross-month patterns
        r'([A-Za-z]{3}\s+\d{1,2}\s*-\s*[A-Za-z]{3}\s+\d{1,2},?\s+\d{4})',  # Oct 31 - Nov 2, 2025
        r'([A-Za-z]{3}\s+\d{1,2}\s*-\s*[A-Za-z]{3}\s+\d{1,2}\s+\d{4})',    # Oct 31 - Nov 2 2025
        
        # Dates without year
        r'([A-Za-z]{3}\s+\d{1,2}\s*-\s*[A-Za-z]{3}\s+\d{1,2})',  # Oct 31 - Nov 2
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            date_found = match.group(1).strip()
            # If no year in the date, add 2025
            if not re.search(r'\d{4}', date_found):
                date_found += ', 2025'
            return date_found
    
    return None

def extract_event_info_from_text(text: str) -> tuple[Optional[str], Optional[str]]:
    """Extract event type and location from text using regex patterns"""
    event_patterns = [
        r'(Battle Hardened):\s*([^,\n]+)',  # Battle Hardened: Seoul
        r'(Calling):\s*([^,\n]+)',          # Calling: Seattle
        r'(World Championship):\s*([^,\n]+)', # World Championship: Philadelphia
        r'(Pro Tour):\s*([^,\n]+)',         # Pro Tour: [Location]
        r'(World Premiere):\s*([^,\n]+)',   # World Premiere: [Location]
    ]
    
    for pattern in event_patterns:
        match = re.search(pattern, text)
        if match:
            if len(match.groups()) == 2:
                event_type = match.group(1).strip()
                location = match.group(2).strip()
                return event_type, location
    
    return None, None

def calculate_date_range_days(date_text: str) -> int:
    """Calculate the number of days in a date range for event duration"""
    try:
        if '-' in date_text:
            parts = date_text.split('-')
            if len(parts) == 2:
                start_part = parts[0].strip()
                end_part = parts[1].strip()
                
                start_match = re.search(r'([A-Za-z]{3})\s+(\d{1,2})', start_part)
                if start_match:
                    start_month = start_match.group(1)
                    start_day = int(start_match.group(2))
                    
                    end_match = re.search(r'([A-Za-z]{3})\s+(\d{1,2})', end_part)
                    if end_match:
                        end_month = end_match.group(1)
                        end_day = int(end_match.group(2))
                        
                        year_match = re.search(r'(\d{4})', date_text)
                        if year_match:
                            year = int(year_match.group(1))
                            
                            month_names = {
                                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                            }
                            
                            start_date = datetime(year, month_names[start_month], start_day)
                            end_date = datetime(year, month_names[end_month], end_day)
                            
                            days_diff = (end_date - start_date).days + 1
                            return days_diff
        
        return 999
    except:
        return 999

def parse_date_to_datetime(date_text: str) -> tuple[Optional[datetime], Optional[datetime]]:
    """Convert date text to datetime objects for calendar event start and end times"""
    try:
        if '-' in date_text:
            parts = date_text.split('-')
            if len(parts) == 2:
                start_part = parts[0].strip()
                end_part = parts[1].strip()
                
                # Check if this is a cross-month date (e.g., "Oct 31 - Nov 2, 2025")
                cross_month_match = re.search(r'([A-Za-z]{3})\s+(\d{1,2})\s*-\s*([A-Za-z]{3})\s+(\d{1,2})', date_text)
                if cross_month_match:
                    start_month = cross_month_match.group(1)
                    start_day = int(cross_month_match.group(2))
                    end_month = cross_month_match.group(3)
                    end_day = int(cross_month_match.group(4))
                    
                    year_match = re.search(r'(\d{4})', date_text)
                    if year_match:
                        year = int(year_match.group(1))
                        
                        month_names = {
                            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                        }
                        
                        start_date = datetime(year, month_names[start_month], start_day)
                        end_date = datetime(year, month_names[end_month], end_day)
                        
                        return start_date, end_date
                
                # Single month date (e.g., "Aug 8-10, 2025")
                start_match = re.search(r'([A-Za-z]{3})\s+(\d{1,2})', start_part)
                if start_match:
                    start_month = start_match.group(1)
                    start_day = int(start_match.group(2))
                    
                    end_match = re.search(r'(\d{1,2})', end_part)
                    if end_match:
                        end_day = int(end_match.group(1))
                        
                        year_match = re.search(r'(\d{4})', date_text)
                        if year_match:
                            year = int(year_match.group(1))
                            
                            month_names = {
                                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                            }
                            
                            start_date = datetime(year, month_names[start_month], start_day)
                            end_date = datetime(year, month_names[start_month], end_day)
                            
                            return start_date, end_date
        
        return None, None
    except Exception as e:
        logger.error(f"Debug: Error parsing date '{date_text}': {e}")
        return None, None

def should_include_event(event_type: str, location: str) -> bool:
    """Determine if an event should be included based on filtering configuration"""
    if not INCLUDE_GLOBAL_MAJORS:
        return False
    
    # Always include major events
    if event_type in ['World Championship', 'Pro Tour', 'World Premiere']:
        return True
    
    # Include Calling events
    if event_type == 'Calling':
        return True
    
    # Include Battle Hardened events (US only if specified)
    if event_type == 'Battle Hardened':
        if INCLUDE_US_BATTLE_HARDENED:
            # Add logic to check if location is in US
            return True
        else:
            return False
    
    return False

def find_all_fab_events() -> List[Dict[str, str]]:
    """Find all FAB events using HTML parsing and regex pattern matching"""
    all_events = []
    
    # Fetch organized play page
    logger.info(f"Fetching global events: {FAB_GLOBAL_URL}")
    html = fetch_page(FAB_GLOBAL_URL)
    
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Method 1: Look for specific patterns in text and find URLs
        all_text = soup.get_text()
        event_matches = re.findall(r'(Battle Hardened|Calling|World Championship|Pro Tour|World Premiere):\s*([^,\n]+)', all_text)
        
        logger.info(f"Found {len(event_matches)} potential event matches in text")
        
        for event_type, location in event_matches:
            event_text = f"{event_type}: {location}"
            event_index = all_text.find(event_text)
            
            if event_index != -1:
                start = max(0, event_index - 200)
                end = min(len(all_text), event_index + 200)
                surrounding_text = all_text[start:end]
                
                date_found = find_date_in_text(surrounding_text)
                
                if date_found:
                    # Try to find the event URL by looking for links near this event
                    event_url = find_event_url(soup, event_type.strip(), location.strip())
                    
                    event = {
                        'type': event_type.strip(),
                        'title': f"{event_type.strip()}: {location.strip()}",
                        'date_text': date_found,
                        'location': location.strip(),
                        'year': '2025',
                        'source': 'text_search',
                        'url': event_url
                    }
                    all_events.append(event)
        
        # Method 2: Look for specific HTML structures
        for tag in soup.find_all(['div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            if tag.find('a'):
                continue
                
            tag_text = tag.get_text()
            if any(event_type in tag_text for event_type in ['Calling:', 'Battle Hardened:', 'World Championship:', 'Pro Tour:']):
                event_type, location = extract_event_info_from_text(tag_text)
                if event_type and location:
                    date_found = find_date_in_text(tag_text)
                    if date_found:
                        # Try to find the event URL
                        event_url = find_event_url(soup, event_type, location)
                        
                        event = {
                            'type': event_type,
                            'title': f"{event_type}: {location}",
                            'date_text': date_found,
                            'location': location,
                            'year': '2025',
                            'source': 'html_structure',
                            'url': event_url
                        }
                        all_events.append(event)
        
        # Deduplicate events
        unique_events = []
        event_lookup = {}
        
        for event in all_events:
            event_key = f"{event['type']}:{event['location']}"
            
            if event_key not in event_lookup:
                event_lookup[event_key] = event
                unique_events.append(event)
            else:
                existing_event = event_lookup[event_key]
                existing_source = existing_event.get('source', 'unknown')
                new_source = event.get('source', 'unknown')
                
                if new_source == 'html_structure' and existing_source == 'text_search':
                    event_lookup[event_key] = event
                    unique_events.remove(existing_event)
                    unique_events.append(event)
        
        logger.info(f"Found {len(unique_events)} unique events after deduplication")
        return unique_events
    
    return []

def find_event_url(soup: BeautifulSoup, event_type: str, location: str) -> Optional[str]:
    """Find the URL for a specific event by searching HTML links and event cards"""
    try:
        # First, try to find the exact event card/link
        # Look for links that contain both the event type and location
        for link in soup.find_all('a', href=True):
            link_text = link.get_text().strip()
            href = link['href']
            
            # Check if this link contains our exact event
            if (event_type in link_text and location in link_text):
                # Make sure it's a relative URL that we can make absolute
                if href.startswith('/'):
                    return f"https://fabtcg.com{href}"
                elif href.startswith('http'):
                    return href
                else:
                    return f"https://fabtcg.com/{href}"
        
        # If no exact match, look for event cards that might contain our event
        # The organized play page has event cards with specific structure
        for card in soup.find_all('div', class_='listblock-item'):
            card_text = card.get_text().strip()
            
            # Check if this card contains our event
            if (event_type in card_text and location in card_text):
                # Look for a link within this card
                link = card.find('a', href=True)
                if link:
                    href = link['href']
                    if href.startswith('/'):
                        return f"https://fabtcg.com{href}"
                    elif href.startswith('http'):
                        return href
                    else:
                        return f"https://fabtcg.com/{href}"
        
        # If still no match, look for any link that might be related
        # but be more careful about matching
        for link in soup.find_all('a', href=True):
            link_text = link.get_text().strip()
            href = link['href']
            
            # Only match if the link text is very similar to our event
            # This prevents false matches like "Calling: Seattle" matching "Calling: Auckland"
            if (event_type in link_text and 
                any(word in link_text for word in location.split()) and
                '/organised-play/' in href):  # Only match organized play links
                
                if href.startswith('/'):
                    return f"https://fabtcg.com{href}"
                elif href.startswith('http'):
                    return href
                else:
                    return f"https://fabtcg.com/{href}"
        
        return None
    except Exception as e:
        logger.error(f"Debug: Error finding URL for {event_type}: {location} - {e}")
        return None

def setup_google_calendar() -> Optional[build]:
    """Set up Google Calendar service using service account credentials"""
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            logger.error(f"Error: Service account file '{SERVICE_ACCOUNT_FILE}' not found")
            return None
        
        if not CALENDAR_ID:
            logger.error("Error: CALENDAR_ID environment variable not set")
            return None
        
        credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('calendar', 'v3', credentials=credentials)
        
        logger.info(f"Successfully connected to Google Calendar: {CALENDAR_ID}")
        return service
    
    except Exception as e:
        logger.error(f"Error setting up Google Calendar: {e}")
        return None

def get_event_color(event_type: str) -> str:
    """Get the appropriate Google Calendar color ID for different event types"""
    # Google Calendar color IDs:
    # 1=Red, 2=Orange, 3=Yellow, 4=Green, 5=Blue, 6=Purple, 7=Pink, 8=Gray, 9=Brown, 10=Default
    
    if event_type in ['World Championship', 'Pro Tour']:
        return '1'  # Red - Tier 1 events (highest)
    elif event_type == 'World Premiere':
        return '2'  # Orange - Tier 2 events
    elif event_type == 'Calling':
        return '4'  # Green - Tier 3 events
    elif event_type == 'Battle Hardened':
        return '5'  # Blue - Tier 4 events
    else:
        return '10'  # Default color for unknown types

def create_calendar_event(service: build, event: Dict[str, str]) -> Optional[Dict[str, str]]:
    """Create a Google Calendar event from FAB event data with proper formatting"""
    try:
        start_date, end_date = parse_date_to_datetime(event['date_text'])
        if not start_date or not end_date:
            logger.warning(f"Could not parse date for {event['title']}: {event['date_text']}")
            return None
        
        # Set end time to end of day
        end_date = end_date + timedelta(days=1)
        
        # Build description with optional URL
        description = f"Flesh and Blood TCG {event['type']} Event\nLocation: {event['location']}\nDate: {event['date_text']}"
        
        if event.get('url'):
            description += f"\n\nEvent Details: {event['url']}"
        
        # Get appropriate color for event type
        color_id = get_event_color(event['type'])
        
        calendar_event = {
            'summary': event['title'],
            'location': event['location'],
            'description': description,
            'start': {
                'date': start_date.strftime('%Y-%m-%d'),
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'date': end_date.strftime('%Y-%m-%d'),
                'timeZone': 'America/Los_Angeles',
            },
            'colorId': color_id,  # Dynamic color based on event type
        }
        
        return calendar_event
    
    except Exception as e:
        logger.error(f"Error creating calendar event for {event['title']}: {e}")
        return None

def sync_events_to_calendar(service: build, events: List[Dict[str, str]]) -> None:
    """Sync FAB events to Google Calendar with duplicate detection and updates"""
    if not service:
        logger.error("No Google Calendar service available")
        return
    
    logger.info(f"Syncing {len(events)} events to Google Calendar...")
    
    success_count = 0
    for event in events:
        if not should_include_event(event['type'], event['location']):
            continue
        
        calendar_event = create_calendar_event(service, event)
        if calendar_event:
            try:
                # Check if event already exists
                existing_events = service.events().list(
                    calendarId=CALENDAR_ID,
                    q=event['title'],
                    timeMin=calendar_event['start']['date'] + 'T00:00:00Z',
                    timeMax=calendar_event['end']['date'] + 'T00:00:00Z'
                ).execute()
                
                if existing_events['items']:
                    # Update existing event
                    event_id = existing_events['items'][0]['id']
                    updated_event = service.events().update(
                        calendarId=CALENDAR_ID,
                        eventId=event_id,
                        body=calendar_event
                    ).execute()
                    logger.info(f"  [UPDATED] {event['title']}")
                else:
                    # Create new event
                    created_event = service.events().insert(
                        calendarId=CALENDAR_ID,
                        body=calendar_event
                    ).execute()
                    logger.info(f"  [CREATED] {event['title']}")
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"  ❌ ERROR: {event['title']} - {e}")
    
    logger.info(f"Successfully synced {success_count} events to calendar")

def get_color_emoji(event_type: str) -> str:
    """Get emoji representation of event color for console display and logging"""
    if event_type in ['World Championship', 'Pro Tour']:
        return '🔴'  # Red
    elif event_type == 'World Premiere':
        return '🟠'  # Orange
    elif event_type == 'Calling':
        return '🟢'  # Green
    elif event_type == 'Battle Hardened':
        return '🔵'  # Blue
    else:
        return '⚪'  # Default

def main():
    """Main function for FAB Major Global Events scraper and calendar sync"""
    logger.info("Starting FAB Major Global Events Scraper & Calendar Sync")
    logger.info("=" * 60)
    
    # Find all FAB events
    logger.info("Finding all FAB events...")
    events = find_all_fab_events()
    
    if not events:
        logger.warning("No events found")
        return
    
    # Display found events with color coding
    logger.info(f"Found {len(events)} events:")
    logger.info("🎨 Color Coding: 🔴 World Championship/Pro Tour | 🟠 World Premiere | 🟢 Calling | 🔵 Battle Hardened")
    logger.info("-" * 80)
    
    for i, event in enumerate(events, 1):
        url_info = f" (URL: {event.get('url', 'No webpage yet')})" if event.get('url') else " (No webpage yet)"
        color_emoji = get_color_emoji(event['type'])
        logger.info(f"{i}. {color_emoji} {event['type']}: {event['location']} - {event['date_text']}{url_info}")
    
    # Set up Google Calendar
    logger.info("Setting up Google Calendar...")
    service = setup_google_calendar()
    
    if service:
        # Sync to calendar
        sync_events_to_calendar(service, events)
        logger.info("Calendar sync completed!")
    else:
        logger.warning("Calendar sync skipped - check CALENDAR_ID in .env file")
    
    logger.info("Script execution completed successfully")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
