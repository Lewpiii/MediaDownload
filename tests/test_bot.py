#!/usr/bin/env python3
"""
Script de test pour identifier les problèmes de téléchargement
"""

import os
import sys
import asyncio
import discord
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

async def test_download_system():
    """Test du système de téléchargement"""
    print("Testing Download System...")
    
    # Vérifier les variables d'environnement
    discord_token = os.getenv('DISCORD_TOKEN')
    topgg_token = os.getenv('TOP_GG_TOKEN')
    
    print(f"Discord Token: {'Found' if discord_token else 'Missing'}")
    print(f"Top.gg Token: {'Found' if topgg_token else 'Missing'}")
    
    if not discord_token:
        print("\nERROR: DISCORD_TOKEN not found!")
        print("Please create a .env file with your Discord bot token:")
        print("DISCORD_TOKEN=your_token_here")
        return False
    
    # Test de connexion Discord
    try:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        bot = discord.Client(intents=intents)
        
        @bot.event
        async def on_ready():
            print(f"Bot connected as {bot.user}")
            print(f"Bot ID: {bot.user.id}")
            
            # Test du système de vote
            if topgg_token:
                print("Top.gg integration available")
            else:
                print("Top.gg integration not configured (will work in open mode)")
            
            await bot.close()
        
        print("Connecting to Discord...")
        await bot.start(discord_token)
        
    except discord.LoginFailure:
        print("ERROR: Invalid Discord token!")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    
    return True

async def test_download_cog():
    """Test du cog de téléchargement"""
    print("\nTesting Download Cog...")
    
    try:
        # Import des modules nécessaires
        from cogs.download import Download, ResourceMonitor
        from utils.smart_classifier import SmartClassifier
        
        print("All download modules imported successfully")
        
        # Test des configurations
        from config import DOWNLOAD_CONFIG
        print(f"Download config loaded: {len(DOWNLOAD_CONFIG)} settings")
        
        # Test du répertoire temporaire
        temp_dir = DOWNLOAD_CONFIG['temp_dir']
        os.makedirs(temp_dir, exist_ok=True)
        print(f"Temp directory ready: {temp_dir}")
        
        return True
        
    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

async def main():
    """Fonction principale de test"""
    print("Media Download Bot - Diagnostic Tool")
    print("=" * 50)
    
    # Test 1: Système Discord
    discord_ok = await test_download_system()
    
    # Test 2: Modules de téléchargement
    modules_ok = await test_download_cog()
    
    print("\n" + "=" * 50)
    print("DIAGNOSTIC RESULTS:")
    print(f"Discord Connection: {'OK' if discord_ok else 'FAILED'}")
    print(f"Download Modules: {'OK' if modules_ok else 'FAILED'}")
    
    if discord_ok and modules_ok:
        print("\nAll tests passed! The bot should work correctly.")
        print("\nNext steps:")
        print("1. Make sure your Discord token is valid")
        print("2. Test the bot with /download command")
        print("3. Check the vote system")
    else:
        print("\nSome tests failed. Please fix the issues above.")
        
        if not discord_ok:
            print("\nTo fix Discord connection:")
            print("1. Create a .env file in the project root")
            print("2. Add: DISCORD_TOKEN=your_bot_token")
            print("3. Get your token from: https://discord.com/developers/applications")

if __name__ == "__main__":
    asyncio.run(main())
