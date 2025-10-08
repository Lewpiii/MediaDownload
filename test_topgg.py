#!/usr/bin/env python3
"""
Script to test Top.gg API configuration
"""
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

async def test_topgg_api():
    """Test Top.gg API connection"""
    print("Testing Top.gg API Configuration...")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    token = os.getenv('TOP_GG_TOKEN')
    bot_id = os.getenv('BOT_ID')  # You'll need to add this
    
    if not token:
        print("❌ TOP_GG_TOKEN not found in environment variables")
        print("\nTo configure:")
        print("1. Go to https://top.gg/bot/YOUR_BOT_ID")
        print("2. Click 'Edit Bot' -> 'Webhooks'")
        print("3. Copy your Authorization token")
        print("4. Add to .env: TOP_GG_TOKEN=your_token_here")
        return False
    
    if not bot_id:
        print("⚠️  BOT_ID not found, using test user ID")
        test_user_id = 123456789  # Replace with a real user ID for testing
    else:
        test_user_id = 123456789  # Replace with a real user ID for testing
    
    print(f"✅ TOP_GG_TOKEN found: {token[:8]}...{token[-4:]}")
    print(f"🧪 Testing with user ID: {test_user_id}")
    
    try:
        headers = {
            'Authorization': token
        }
        
        # Test API endpoint
        url = f"https://top.gg/api/bots/{bot_id or 'YOUR_BOT_ID'}/check?userId={test_user_id}"
        print(f"🌐 Testing API: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                print(f"📡 Response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"📊 Response data: {data}")
                    
                    voted = data.get('voted', 0) == 1
                    print(f"🗳️  User voted: {voted}")
                    
                    if voted:
                        print("✅ Vote verification working correctly!")
                    else:
                        print("ℹ️  User hasn't voted (this is normal for testing)")
                    
                    return True
                    
                elif response.status == 401:
                    print("❌ Authentication failed - check your TOP_GG_TOKEN")
                    return False
                    
                elif response.status == 404:
                    print("❌ Bot not found - check your BOT_ID")
                    return False
                    
                else:
                    print(f"❌ API error: {response.status}")
                    text = await response.text()
                    print(f"Error details: {text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def main():
    """Main function"""
    print("Top.gg API Test Tool")
    print("=" * 50)
    
    # Check if required packages are installed
    try:
        import aiohttp
    except ImportError:
        print("❌ aiohttp not installed")
        print("Install with: pip install aiohttp")
        return
    
    # Run the test
    result = asyncio.run(test_topgg_api())
    
    print("=" * 50)
    if result:
        print("🎉 Top.gg API configuration is working!")
    else:
        print("⚠️  Top.gg API configuration needs attention")
        print("\nNext steps:")
        print("1. Verify your TOP_GG_TOKEN is correct")
        print("2. Make sure your bot is listed on top.gg")
        print("3. Check the bot ID in the API URL")

if __name__ == "__main__":
    main()
