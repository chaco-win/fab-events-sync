#!/usr/bin/env python3
"""
Simple log viewer for FAB Events Sync logs
"""

import os
import glob
from datetime import datetime

def view_logs():
    """View recent log files"""
    logs_dir = "logs"
    
    if not os.path.exists(logs_dir):
        print("No logs directory found. Run the scripts first to generate logs.")
        return
    
    # Find all log files
    log_files = glob.glob(os.path.join(logs_dir, "*.log"))
    
    if not log_files:
        print("No log files found.")
        return
    
    # Sort by modification time (newest first)
    log_files.sort(key=os.path.getmtime, reverse=True)
    
    print("FAB Events Sync Log Files:")
    print("=" * 50)
    
    for log_file in log_files[:5]:  # Show last 5 logs
        mod_time = datetime.fromtimestamp(os.path.getmtime(log_file))
        file_size = os.path.getsize(log_file)
        file_name = os.path.basename(log_file)
        
        print(f"{file_name}")
        print(f"  Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Size: {file_size:,} bytes")
        print()
    
    # Show latest log content
    if log_files:
        latest_log = log_files[0]
        print(f"Latest log content ({os.path.basename(latest_log)}):")
        print("=" * 50)
        
        try:
            with open(latest_log, 'r') as f:
                lines = f.readlines()
                # Show last 20 lines
                for line in lines[-20:]:
                    print(line.rstrip())
        except Exception as e:
            print(f"Error reading log file: {e}")

if __name__ == "__main__":
    view_logs()
