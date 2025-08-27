# FAB Events Sync - Configuration Guide

This guide explains all configuration options, environment variables, and settings for the FAB Events Sync system.

## 🔧 **Configuration Overview**

The system is configured through several methods:
- **Environment variables** (`.env` file)
- **Configuration files** (`sa.json`, `crontab`)
- **Script-specific settings** (hardcoded in Python files)

## 📁 **Environment Variables (.env file)**

### **Google Calendar Configuration**

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `LOCAL_CALENDAR_ID` | Google Calendar ID for local DFW events | `abc123@group.calendar.google.com` | ✅ Yes |
| `MAJOR_CALENDAR_ID` | Google Calendar ID for major global events | `def456@group.calendar.google.com` | ✅ Yes |

### **Discord Configuration**

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `DISCORD_WEBHOOK_URL` | Discord webhook URL for notifications | `https://discord.com/api/webhooks/...` | ❌ No |

### **FAB Events Configuration**

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `FAB_LOCAL_URL` | Base URL for FAB local events | `https://fabtcg.com/en/events/` | ❌ No |
| `SEARCH_LOCATION` | Default search location for events | `Fort Worth, TX 76117, USA` | ❌ No |
| `MAX_DISTANCE_COMPETITIVE` | Max distance for competitive events (miles) | `250` | ❌ No |
| `MAX_DISTANCE_PRERELEASE` | Max distance for prerelease events (miles) | `100` | ❌ No |
| `REQUEST_DELAY` | Delay between API requests (seconds) | `1` | ❌ No |

## 📋 **Example .env File**

```bash
# Google Calendar Configuration
LOCAL_CALENDAR_ID=your_local_calendar_id_here
MAJOR_CALENDAR_ID=your_major_calendar_id_here

# Discord Configuration
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_here

# FAB Events Configuration
FAB_LOCAL_URL=https://fabtcg.com/en/events/
SEARCH_LOCATION=Fort Worth, TX 76117, USA
MAX_DISTANCE_COMPETITIVE=250
MAX_DISTANCE_PRERELEASE=100
REQUEST_DELAY=1
```

## 🔑 **Google API Credentials (sa.json)**

### **File Location**
- **Path**: `./sa.json` (project root directory)
- **Permissions**: `600` (owner read/write only)
- **Format**: JSON service account key file

### **Required Permissions**
The service account needs access to:
- **Google Calendar API**: Read/write access to specified calendars
- **Calendar Access**: Share calendars with the service account email

### **Security Considerations**
```bash
# Set proper file permissions
chmod 600 sa.json

# Verify permissions
ls -la sa.json
# Should show: -rw------- 1 user user 1234 Aug 27 10:00 sa.json
```

## ⏰ **Cron Job Configuration**

### **Crontab Entries**

```bash
# Health check - runs weekly on Tuesday at 6 PM
0 18 * * 2 /usr/local/bin/python /app/health_check.py

# FAB Local DFW Events - runs weekly on Wednesday at 1 AM
0 1 * * 3 /usr/local/bin/python /app/fab_local_dfw_events.py

# FAB Major Global Events - runs weekly on Wednesday at 2 AM
0 2 * * 3 /usr/local/bin/python /app/fab_major_global_events.py
```

### **Cron Schedule Format**
```
┌───────────── minute (0-59)
│ ┌─────────── hour (0-23)
│ │ ┌───────── day of month (1-31)
│ │ │ ┌───────── month (1-12)
│ │ │ │ ┌───── day of week (0-7, Sunday=0 or 7)
│ │ │ │ │
* * * * * command
```

### **Time Zone Considerations**
- **Server timezone** affects when cron jobs run
- **Check server timezone**: `timedatectl`
- **Change timezone**: `sudo timedatectl set-timezone America/Chicago`

## 🐳 **Docker Configuration (docker-compose.yml)**

### **Container Settings**
```yaml
services:
  fab-events-sync:
    build: .
    container_name: fab-events-sync
    volumes:
      - .:/app
      - ./logs:/app/logs
    environment:
      - TZ=America/Chicago
    restart: unless-stopped
```

### **Volume Mappings**
- **`.:/app`**: Project files mounted to container
- **`./logs:/app/logs`**: Log files accessible from host

### **Environment Variables**
- **`TZ`**: Container timezone
- **`restart`**: Container restart policy

## 📊 **Logging Configuration**

### **Log File Structure**
```
logs/
├── health_check_YYYYMMDD_HHMMSS.log
├── fab_local_dfw_events_YYYYMMDD_HHMMSS.log
└── fab_major_global_events_YYYYMMDD_HHMMSS.log
```

### **Log Format**
```
YYYY-MM-DD HH:MM:SS,mmm - LEVEL - Message
```

### **Log Levels**
- **INFO**: General information and status updates
- **WARNING**: Non-critical issues
- **ERROR**: Critical errors and failures
- **DEBUG**: Detailed debugging information

### **Log Rotation**
```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/fab-events-sync

# Add configuration
/home/user/fab-events-sync/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 user user
}
```

## 🔍 **Script-Specific Configuration**

### **Health Check Script (health_check.py)**

#### **Configuration Options**
- **Log directory**: `logs/`
- **Log file prefix**: `health_check_`
- **Health check frequency**: Weekly (Tuesday 6 PM)
- **Discord notifications**: Only on failures

#### **Customization**
```python
# Modify log directory
log_dir = Path("custom_logs")

# Change notification behavior
send_notifications_on_success = True
```

### **Local Events Script (fab_local_dfw_events.py)**

#### **Configuration Options**
- **Search radius**: 250 miles (competitive), 100 miles (prerelease)
- **Event types**: Competitive events only
- **Location**: Fort Worth, TX area
- **Update frequency**: Weekly (Wednesday 1 AM)

#### **Customization**
```python
# Modify search parameters
MAX_DISTANCE_COMPETITIVE = 300  # Increase to 300 miles
SEARCH_LOCATION = "Dallas, TX 75201, USA"  # Change location
```

### **Major Events Script (fab_major_global_events.py)**

#### **Configuration Options**
- **Event types**: Organized Play events
- **Geographic scope**: Worldwide
- **Update frequency**: Weekly (Wednesday 2 AM)
- **Event filtering**: Major competitive events only

#### **Customization**
```python
# Modify event filtering
MINIMUM_PLAYERS = 16  # Only events with 16+ players
EVENT_TYPES = ['Pro Tour', 'National Championship']  # Specific event types
```

## 🌍 **Environment-Specific Configuration**

### **Development Environment**
```bash
# Development settings
LOG_LEVEL=DEBUG
REQUEST_DELAY=0.5
TEST_MODE=true
```

### **Production Environment**
```bash
# Production settings
LOG_LEVEL=INFO
REQUEST_DELAY=1
TEST_MODE=false
```

### **Testing Environment**
```bash
# Testing settings
LOG_LEVEL=DEBUG
REQUEST_DELAY=0.1
TEST_MODE=true
MOCK_GOOGLE_API=true
```

## 🔒 **Security Configuration**

### **File Permissions**
```bash
# Secure sensitive files
chmod 600 sa.json
chmod 600 .env
chmod 700 ~/fab-events-sync

# Verify permissions
ls -la sa.json .env
```

### **Network Security**
- **Firewall**: Restrict access to necessary ports only
- **SSH**: Use key-based authentication
- **Docker**: Run containers with minimal privileges

### **API Security**
- **Google API**: Use service account with minimal permissions
- **Discord Webhook**: Keep webhook URLs private
- **Environment Variables**: Don't commit `.env` files to version control

## 📈 **Performance Configuration**

### **Resource Limits**
```yaml
# Docker resource limits
services:
  fab-events-sync:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

### **Request Throttling**
```python
# Adjust request delays
REQUEST_DELAY = 2  # 2 seconds between requests
MAX_CONCURRENT_REQUESTS = 3  # Limit concurrent API calls
```

### **Logging Performance**
```python
# Optimize logging
LOG_LEVEL = "INFO"  # Reduce debug logging in production
LOG_ROTATION_SIZE = "10MB"  # Rotate logs at 10MB
LOG_RETENTION_DAYS = 30  # Keep logs for 30 days
```

## 🔄 **Update and Maintenance Configuration**

### **Auto-Update Settings**
```bash
# Git pull frequency
# Add to crontab for daily updates
0 2 * * * cd /home/user/fab-events-sync && git pull

# Container rebuild frequency
# Add to crontab for weekly rebuilds
0 3 * * 0 cd /home/user/fab-events-sync && docker compose down && docker compose up --build -d
```

### **Backup Configuration**
```bash
# Backup important files
# Add to crontab for daily backups
0 1 * * * tar -czf /backup/fab-events-sync-$(date +\%Y\%m\%d).tar.gz /home/user/fab-events-sync/sa.json /home/user/fab-events-sync/.env
```

## 📝 **Configuration Validation**

### **Health Check Validation**
```bash
# Run configuration validation
docker compose exec fab-events-sync python health_check.py

# Check specific configuration
docker compose exec fab-events-sync python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(f'LOCAL_CALENDAR_ID: {os.getenv(\"LOCAL_CALENDAR_ID\")}')
print(f'MAJOR_CALENDAR_ID: {os.getenv(\"MAJOR_CALENDAR_ID\")}')
"
```

### **Environment Variable Check**
```bash
# Verify all required variables are set
docker compose exec fab-events-sync env | grep -E "(LOCAL_CALENDAR_ID|MAJOR_CALENDAR_ID|DISCORD_WEBHOOK_URL)"
```

## 🚨 **Troubleshooting Configuration Issues**

### **Common Configuration Problems**

#### **Missing Environment Variables**
```bash
# Check if .env file exists
ls -la .env

# Verify variable loading
docker compose exec fab-events-sync printenv | grep CALENDAR
```

#### **Invalid Calendar IDs**
```bash
# Test calendar access
docker compose exec fab-events-sync python -c "
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
creds = Credentials.from_service_account_file('sa.json')
service = build('calendar', 'v3', credentials=creds)
cal = service.calendars().get(calendarId='YOUR_CALENDAR_ID').execute()
print(f'Calendar: {cal[\"summary\"]}')
"
```

#### **Permission Issues**
```bash
# Check file permissions
ls -la sa.json .env

# Fix permissions if needed
chmod 600 sa.json .env
```
