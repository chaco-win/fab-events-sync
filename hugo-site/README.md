# FAB Events Hugo Site

This is a simple Hugo static site that provides a link tree for subscribing to FAB TCG event calendars.

## 🎯 **What This Is**

A clean, modern landing page at `chaco.dev/fabevents` that allows users to:
- Subscribe to Global Events calendar
- Subscribe to Local DFW Events calendar  
- Support the project via donations

## 🏗️ **Site Structure**

```
hugo-site/
├── config.toml          # Hugo configuration
├── content/             # Content files
├── layouts/             # HTML templates
├── static/              # CSS, images, etc.
├── docker-compose.yml   # Docker setup
├── nginx.conf          # Nginx configuration
└── README.md           # This file
```

## 🚀 **Quick Start**

### **1. Build the Site**
```bash
# Build static files
docker compose up hugo

# The site will be generated in ./public/
```

### **2. Serve Locally**
```bash
# Start nginx to serve the site
docker compose up nginx

# Visit http://localhost:8080
```

### **3. Deploy to Server**
```bash
# Build and copy to your server
docker compose up --build
```

## 🌐 **Docker Network**

This Hugo site runs on its own dedicated Docker network (`fab-events-web`) to ensure:
- **Network isolation** from other services
- **Clean separation** of web traffic
- **Easy management** without affecting other containers
- **Port conflict prevention** with other services

## 🔧 **Customization**

### **Update Calendar IDs**
Edit `content/_index.md` and replace:
- `YOUR_MAJOR_CALENDAR_ID` with your actual Google Calendar ID
- `YOUR_LOCAL_CALENDAR_ID` with your actual Google Calendar ID

### **Update Donation Link**
Edit `content/_index.md` and replace:
- `https://paypal.me/yourusername` with your actual donation link

### **Customize Styling**
Edit `static/css/style.css` to change colors, fonts, and layout.

## 🌐 **Deployment**

This site is designed to be served via Cloudflare Tunnel at `chaco.dev/fabevents`.

The Hugo site generates static files that can be served by any web server or CDN.

## 📱 **Features**

- **Responsive design** - works on all devices
- **Modern UI** - clean, professional appearance
- **Fast loading** - static files, no backend
- **Easy updates** - just edit content files and rebuild
