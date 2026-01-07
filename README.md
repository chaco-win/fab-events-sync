# FAB Events Sync

## Project Links
- Live site: https://fabevents.chaco.dev
- Data folder: `data/` (e.g., `global_events.json`, `dfw_events.json`)
- Discord Bot: `discord-bot/README.md`

A comprehensive system for automatically synchronizing Flesh and Blood (FAB) TCG events to Google Calendar. This project scrapes competitive events from the official FAB website and local event locator, then automatically adds them to your Google Calendar with proper categorization and details.

## 🎯 **What This Project Does**

- **Automatically scrapes** competitive FAB events from official sources
- **Syncs to Google Calendar** with proper event details and categorization
- **Handles two event types**:
  - **Local DFW Events**: Competitive events within 250 miles of Fort Worth, TX
  - **Major Global Events**: Organized Play events worldwide
- **Weekly health monitoring** to ensure system reliability
- **Automated scheduling** via cron jobs
- **Discord notifications** for system health and failures

## ✨ **Features**

- 🕐 **Automated Scheduling**: Runs weekly via cron jobs
- 📅 **Google Calendar Integration**: Seamless calendar management
- 🔍 **Smart Event Filtering**: Competitive events only, distance-based filtering
- 📊 **Health Monitoring**: Weekly system health checks
- 🚨 **Discord Alerts**: Notifications for system issues
- 🐳 **Docker Containerization**: Easy deployment and management
- 📝 **Comprehensive Logging**: Detailed logs for troubleshooting
- 🔄 **Incremental Updates**: Only adds new events, doesn't duplicate

## 🚀 **Quick Start**

### **Prerequisites**
- Docker and Docker Compose installed
- Google Calendar API credentials (`sa.json`)
- Discord webhook URL (for notifications)

### **1. Clone the Repository**
```bash
git clone https://github.com/yourusername/fab-events-sync.git
cd fab-events-sync
```

### **2. Configure Environment**
```bash
# Copy and edit the environment file
cp .env.example .env
# Edit .env with your settings
```

### **3. Add Google API Credentials**
- Place your `sa.json` file in the project root
- Ensure the service account has access to your Google Calendar

### **4. Start the System**
```bash
docker compose up -d
```

### **5. Verify Installation**
```bash
docker compose exec fab-events-sync python health_check.py
```

### **Manual Script Runs (Docker)**
```bash
# Run local DFW events sync
docker compose exec fab-events-sync python fab_local_dfw_events.py

# Run major global events sync
docker compose exec fab-events-sync python fab_major_global_events.py

# Run health check
docker compose exec fab-events-sync python health_check.py

# Clear calendars (prompts before deleting)
docker compose exec fab-events-sync python clean_calendar.py
```

## 📋 **System Requirements**

- **OS**: Linux (Ubuntu 20.04+ recommended)
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.11+ (handled by Docker)
- **Memory**: 2GB+ RAM
- **Storage**: 5GB+ free space

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cron Jobs     │───▶│  Python Scripts │───▶│ Google Calendar │
│ (Weekly Tasks)  │    │ (Event Scraping)│    │ (Event Storage) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Health Check   │    │   Event Data    │    │  Discord Bot    │
│ (System Monitor)│    │ (FAB Website)   │    │ (Notifications) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 **Project Structure**

```
fab-events-sync/
├── docker-compose.yml          # Container configuration
├── health_check.py             # System health monitoring
├── fab_local_dfw_events.py    # Local DFW events scraper
├── fab_major_global_events.py # Major global events scraper
├── clean_calendar.py          # Calendar cleanup utility
├── requirements.txt            # Python dependencies
├── sa.json                    # Google API credentials
├── .env                       # Environment configuration
├── COMMANDS.md                # Command reference guide
├── SETUP.md                   # Detailed setup instructions
├── CONFIGURATION.md           # Configuration options
└── logs/                      # Application logs
```

## ⏰ **Scheduled Tasks**

| Task | Schedule | Description |
|------|----------|-------------|
| **Health Check** | Tuesday 6:00 PM | System health verification |
| **Local Events** | Wednesday 1:00 AM | Sync DFW competitive events |
| **Major Events** | Wednesday 2:00 AM | Sync global organized play |

## 🔧 **Configuration**

The system is configured through environment variables and configuration files:

- **`.env`**: Main configuration file
- **`sa.json`**: Google Calendar API credentials
- **`crontab`**: Scheduled task configuration

See [CONFIGURATION.md](CONFIGURATION.md) for detailed configuration options.

