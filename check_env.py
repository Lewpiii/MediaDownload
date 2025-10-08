#!/usr/bin/env python3
"""
Script to check environment variables for the Discord bot
"""
import os
from dotenv import load_dotenv

def check_env_variables():
    """Check if all required environment variables are set"""
    print("Checking Environment Variables...")
    print("=" * 50)
    
    # Load .env file if it exists
    load_dotenv()
    
    # Required variables
    variables = {
        'DISCORD_TOKEN': 'Discord Bot Token',
        'TOP_GG_TOKEN': 'Top.gg API Token', 
        'LOGS_CHANNEL_ID': 'Logs Channel ID',
        'WEBHOOK_URL': 'Webhook URL',
        'GOFILE_TOKEN': 'GoFile Token'
    }
    
    all_good = True
    
    for var_name, description in variables.items():
        value = os.getenv(var_name)
        if value:
            # Hide sensitive tokens
            if 'TOKEN' in var_name:
                display_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
            else:
                display_value = value
            print(f"OK  {var_name}: {display_value}")
        else:
            print(f"NO  {var_name}: NOT SET")
            all_good = False
    
    print("=" * 50)
    
    if all_good:
        print("All environment variables are configured!")
    else:
        print("Some environment variables are missing.")
        print("\nTo configure missing variables:")
        print("1. Create a .env file in the project root")
        print("2. Add the missing variables:")
        for var_name, description in variables.items():
            if not os.getenv(var_name):
                print(f"   {var_name}=your_{var_name.lower()}_here")
        print("\nFor TOP_GG_TOKEN:")
        print("   - Go to https://top.gg/bot/YOUR_BOT_ID")
        print("   - Click 'Edit Bot' -> 'Webhooks'")
        print("   - Copy your Authorization token")
    
    return all_good

if __name__ == "__main__":
    check_env_variables()