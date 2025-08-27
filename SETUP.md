# FAB Events Sync - Setup Guide

This guide provides detailed step-by-step instructions for setting up the FAB Events Sync system on your server.

## 📋 **Prerequisites**

Before you begin, ensure you have:

- **Server Access**: SSH access to a Linux server (Ubuntu 20.04+ recommended)
- **Domain/Server**: A server with a public IP address
- **Google Account**: Access to Google Calendar and Google Cloud Console
- **Discord Server**: A Discord server for notifications (optional but recommended)

## 🚀 **Step 1: Server Preparation**

### **1.1 Update System**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget
```

### **1.2 Install Docker**
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker compose version
```

### **1.3 Install Git**
```bash
sudo apt install -y git
git --version
```

## 🔑 **Step 2: Google Calendar API Setup**

### **2.1 Create Google Cloud Project**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Calendar API
4. Go to "APIs & Services" → "Credentials"

### **2.2 Create Service Account**
1. Click "Create Credentials" → "Service Account"
2. Fill in service account details:
   - **Name**: `fab-events-sync`
   - **Description**: `Service account for FAB Events Sync system`
3. Click "Create and Continue"
4. Skip role assignment (we'll handle permissions separately)
5. Click "Done"

### **2.3 Generate Service Account Key**
1. Click on your service account name
2. Go to "Keys" tab
3. Click "Add Key" → "Create New Key"
4. Choose "JSON" format
5. Download the key file and rename it to `sa.json`

### **2.4 Set Calendar Permissions**
1. Go to [Google Calendar](https://calendar.google.com/)
2. Find your calendar in the left sidebar
3. Click the three dots → "Settings and sharing"
4. Under "Share with specific people", add your service account email
5. Grant "Make changes to events" permission

## 🎯 **Step 3: Discord Webhook Setup (Optional)**

### **3.1 Create Discord Webhook**
1. Go to your Discord server
2. Right-click on the channel for notifications
3. Select "Edit Channel" → "Integrations" → "Webhooks"
4. Click "New Webhook"
5. Give it a name (e.g., "FAB Events Health")
6. Copy the webhook URL

## 📥 **Step 4: Clone and Configure Repository**

### **4.1 Clone Repository**
```bash
cd ~
git clone https://github.com/yourusername/fab-events-sync.git
cd fab-events-sync
```

### **4.2 Add Credentials**
```bash
# Copy your Google API credentials
cp /path/to/your/sa.json ./

# Verify the file is in place
ls -la sa.json
```

### **4.3 Create Environment File**
```bash
# Create .env file
cat > .env << EOF
# Google Calendar Configuration
LOCAL_CALENDAR_ID=your_local_calendar_id_here
MAJOR_CALENDAR_ID=your_major_calendar_id_here

# Discord Configuration
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here

# FAB Events Configuration
FAB_LOCAL_URL=https://fabtcg.com/en/events/
SEARCH_LOCATION=Fort Worth, TX 76117, USA
MAX_DISTANCE_COMPETITIVE=250
MAX_DISTANCE_PRERELEASE=100
REQUEST_DELAY=1
EOF

# Edit the file with your actual values
nano .env
```

### **4.4 Get Calendar IDs**
1. Go to [Google Calendar](https://calendar.google.com/)
2. Find your calendars in the left sidebar
3. Click the three dots → "Settings and sharing"
4. Scroll down to "Integrate calendar"
5. Copy the "Calendar ID" (looks like: `abc123@group.calendar.google.com`)

## 🐳 **Step 5: Docker Setup**

### **5.1 Build and Start Container**
```bash
# Build the container
docker compose up --build -d

# Check container status
docker compose ps

# View logs
docker compose logs -f fab-events-sync
```

### **5.2 Verify Installation**
```bash
# Run health check
docker compose exec fab-events-sync python health_check.py

# Expected output: All checks should pass
```

## ⏰ **Step 6: Cron Job Setup**

### **6.1 Edit Crontab**
```bash
crontab -e
```

### **6.2 Add Cron Jobs**
```bash
# Health check - runs weekly on Tuesday at 6 PM
0 18 * * 2 /usr/local/bin/python /app/health_check.py

# FAB Local DFW Events - runs weekly on Wednesday at 1 AM
0 1 * * 3 /usr/local/bin/python /app/fab_local_dfw_events.py

# FAB Major Global Events - runs weekly on Wednesday at 2 AM
0 2 * * 3 /usr/local/bin/python /app/fab_major_global_events.py
```

### **6.3 Verify Cron Jobs**
```bash
# List cron jobs
crontab -l

# Check cron service status
sudo systemctl status cron
```

## 🧪 **Step 7: Testing**

### **7.1 Test Health Check**
```bash
docker compose exec fab-events-sync python health_check.py
```

### **7.2 Test Event Scripts**
```bash
# Test local events (small test)
docker compose exec fab-events-sync python fab_local_dfw_events.py

# Test major events (larger test)
docker compose exec fab-events-sync python fab_major_global_events.py
```

### **7.3 Check Google Calendar**
1. Go to your Google Calendar
2. Verify events are being added
3. Check event details and formatting

## 🔧 **Step 8: Troubleshooting**

### **8.1 Common Issues**

#### **Container Won't Start**
```bash
# Check Docker status
sudo systemctl status docker

# Check container logs
docker compose logs fab-events-sync

# Force rebuild
docker compose down --rmi all --volumes
docker compose up --build -d
```

#### **Google API Errors**
```bash
# Verify sa.json exists
ls -la sa.json

# Check file permissions
chmod 600 sa.json

# Verify service account has calendar access
```

#### **Cron Job Failures**
```bash
# Check cron logs
sudo grep CRON /var/log/syslog | tail -20

# Test cron job manually
docker compose exec fab-events-sync python health_check.py
```

### **8.2 Log Analysis**
```bash
# View recent logs
docker compose exec fab-events-sync tail -f logs/health_check_*.log

# Check specific script logs
docker compose exec fab-events-sync tail -f logs/fab_local_dfw_events_*.log
```

## ✅ **Step 9: Verification Checklist**

- [ ] Docker container is running
- [ ] Health check passes all tests
- [ ] Google Calendar API is accessible
- [ ] Cron jobs are configured
- [ ] Test events are added to calendar
- [ ] Discord notifications are working
- [ ] Logs are being generated

## 🚀 **Step 10: Production Deployment**

### **10.1 Security Considerations**
```bash
# Secure file permissions
chmod 600 sa.json
chmod 600 .env

# Restrict access to project directory
chmod 700 ~/fab-events-sync
```

### **10.2 Monitoring Setup**
```bash
# Set up log rotation
sudo nano /etc/logrotate.d/fab-events-sync

# Monitor disk space
df -h

# Monitor container resources
docker stats fab-events-sync
```
