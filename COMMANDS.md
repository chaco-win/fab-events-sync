# FAB Events Sync - Commands Reference

This document contains all the important commands for managing the FAB Events Sync system.

## 🐳 **Docker Container Management**

### **Start/Stop Services**
```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart services
docker compose restart

# View running containers
docker compose ps
```

### **Rebuild Container**
```bash
# Force complete rebuild (use when code changes aren't working)
docker compose down --rmi all --volumes
docker compose up --build -d
```

## 🔍 **Health Check**

### **Run Health Check**
```bash
# Basic health check
docker compose exec fab-events-sync python health_check.py

# Health check with detailed output
docker compose exec fab-events-sync python health_check.py 2>&1 | tee health_check_output.log
```

## 🧹 **Calendar Management**

### **Clean Calendars**
```bash
# Clean all calendars (removes all events)
docker compose exec fab-events-sync python clean_calendar.py
```

### **Rebuild Calendars**
```bash
# Rebuild Local DFW Events Calendar
docker compose exec fab-events-sync python fab_local_dfw_events.py

# Rebuild Major Global Events Calendar
docker compose exec fab-events-sync python fab_major_global_events.py
```

### **Complete Calendar Reset**
```bash
# 1. Clean all calendars
docker compose exec fab-events-sync python clean_calendar.py

# 2. Rebuild Local DFW Events
docker compose exec fab-events-sync python fab_local_dfw_events.py

# 3. Rebuild Major Global Events
docker compose exec fab-events-sync python fab_major_global_events.py
```

## 📊 **Monitoring & Logs**

### **View Logs**
```bash
# View all container logs
docker compose logs fab-events-sync

# Follow logs in real-time
docker compose logs -f fab-events-sync

# View logs for specific script
docker compose exec fab-events-sync tail -f logs/[script_name]_*.log
```

### **Check Container Status**
```bash
# Check if container is running
docker compose ps

# Check container resource usage
docker stats fab-events-sync
```

## 🔧 **Troubleshooting**

### **Force Container Rebuild**
```bash
# When code changes aren't working
docker compose down --rmi all --volumes
docker system prune -a --force
git pull
docker compose up --build -d
```

### **Check File Changes**
```bash
# Verify files are updated in container
docker compose exec fab-events-sync cat health_check.py | head -20

# Compare local vs container files
diff health_check.py <(docker compose exec fab-events-sync cat health_check.py)
```

### **Python Environment Check**
```bash
# Check Python version in container
docker compose exec fab-events-sync python --version

# Check installed packages
docker compose exec fab-events-sync pip list | grep google
```

## 📁 **File Management**

### **Access Container Shell**
```bash
# Get interactive shell in container
docker compose exec fab-events-sync bash

# Run single command in container
docker compose exec fab-events-sync ls -la
```

### **Copy Files**
```bash
# Copy file from container to host
docker compose cp fab-events-sync:/app/logs/health_check_*.log ./

# Copy file from host to container
docker compose cp health_check.py fab-events-sync:/app/
```

## ⏰ **Cron Job Management**

### **Check Cron Status**
```bash
# View cron jobs
crontab -l

# Check cron service status
sudo systemctl status cron

# Check cron logs
sudo grep CRON /var/log/syslog | tail -20
```

### **Test Cron Jobs Manually**
```bash
# Test health check manually
docker compose exec fab-events-sync python health_check.py

# Test local events script manually
docker compose exec fab-events-sync python fab_local_dfw_events.py

# Test major events script manually
docker compose exec fab-events-sync python fab_major_global_events.py
```

## 🚨 **Emergency Commands**

### **Complete System Reset**
```bash
# Stop everything
docker compose down --rmi all --volumes

# Clear all Docker data
docker system prune -a --force

# Pull latest code
git pull

# Rebuild from scratch
docker compose up --build -d

# Verify health
docker compose exec fab-events-sync python health_check.py
```

### **Quick Health Check**
```bash
# Fast health verification
docker compose ps && docker compose exec fab-events-sync python health_check.py
```
