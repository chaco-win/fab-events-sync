#!/usr/bin/env python3
"""
Quick Discord Webhook Test Script

This script tests if the Discord webhook is working correctly.
"""

import os
import requests
from dotenv import load_dotenv

def test_discord_webhook():
    """Test the Discord webhook connection."""
    # Load environment variables
    load_dotenv(dotenv_path='.env', override=False)
    import os
    if os.path.exists('.env.local'):
        load_dotenv(dotenv_path='.env.local', override=True)
    
    # Get webhook URL
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    if not webhook_url:
        print("❌ ERROR: No DISCORD_WEBHOOK_URL found in .env file")
        return False
    
    print(f"🔗 Testing Discord webhook...")
    print(f"URL: {webhook_url[:50]}...")
    
    try:
        # Send test message
        test_message = "🧪 **Discord Webhook Test**\nThis is a test message from your FAB Events Sync system!"
        
        data = {"content": test_message}
        response = requests.post(webhook_url, json=data)
        
        if response.status_code == 204:
            print("✅ SUCCESS: Discord webhook is working!")
            print("📱 Check your Discord channel for the test message")
            return True
        else:
            print(f"❌ ERROR: Discord webhook failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Failed to send Discord message: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Discord Webhook Test")
    print("=" * 40)
    
    success = test_discord_webhook()
    
    print("=" * 40)
    if success:
        print("🎉 Test completed successfully!")
    else:
        print("💥 Test failed - check your configuration")
