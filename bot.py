import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import io
from datetime import datetime
import asyncio
import sys
import traceback
import aiohttp
import time
import tempfile
import subprocess
import topgg
from counters import download_count, successful_downloads, failed_downloads
import requests
from dotenv import load_dotenv
import json
from pathlib import Path
import zipfile
from utils.logging import Logger

# Configuration
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
LOGS_CHANNEL_ID = os.getenv('LOGS_CHANNEL_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
GOFILE_TOKEN = os.getenv('GOFILE_TOKEN')
TOP_GG_TOKEN = os.getenv('TOP_GG_TOKEN')

# Debug
print("=== Debug Discord Bot ===")
print(f"Token exists: {'Yes' if TOKEN else 'No'}")
print(f"Logs Channel ID: {LOGS_CHANNEL_ID}")
print(f"Webhook URL exists: {'Yes' if WEBHOOK_URL else 'No'}")
print("=======================")

if not TOKEN:
    raise ValueError("❌ Discord Token not found!")

try:
    LOGS_CHANNEL_ID = int(LOGS_CHANNEL_ID) if LOGS_CHANNEL_ID else None
except ValueError as e:
    print(f"❌ Error converting channel IDs: {e}")

class MediaDownloadBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True  # Ajouté pour les logs de serveur
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        # Types de médias supportés
        self.media_types = {
            'images': ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
            'videos': ['.mp4', '.webm', '.mov'],
            'all': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.webm', '.mov']
        }
        
        # Initialiser le logger
        self.logger = Logger(self)

    async def setup_hook(self):
        """Configuration initiale du bot"""
        # Charger les cogs
        await self.load_extension('cogs.download')
        await self.load_extension('cogs.help')
        await self.load_extension('cogs.stats')
        await self.load_extension('cogs.feedback')
        print("✓ All cogs loaded")
        
        # Démarrer la tâche de heartbeat
        self.heartbeat_task = self.loop.create_task(self.heartbeat_check())

    async def heartbeat_check(self):
        """Vérifie périodiquement l'état du bot"""
        log_channel = self.get_channel(int(os.getenv('LOGS_CHANNEL_ID')))
        last_status = True
        
        while not self.is_closed():
            try:
                latency = round(self.latency * 1000)
                if last_status:
                    embed = discord.Embed(
                        title="🟢 Bot Status",
                        description=f"Bot is running\nLatency: {latency}ms",
                        color=0x00FF00
                    )
                else:
                    embed = discord.Embed(
                        title="✅ Bot Recovery",
                        description=f"Bot is back online\nLatency: {latency}ms",
                        color=0xFFAA00
                    )
                    last_status = True
                await log_channel.send(embed=embed)
            except Exception as e:
                if last_status:
                    try:
                        error_embed = discord.Embed(
                            title="🔴 Bot Offline",
                            description=f"Bot is experiencing issues\nError: {str(e)}",
                            color=0xFF0000
                        )
                        await log_channel.send(embed=error_embed)
                    except:
                        pass
                    last_status = False
            await asyncio.sleep(300)

    async def on_guild_join(self, guild):
        """Log quand le bot rejoint un serveur"""
        await self.logger.log_guild_join(guild)

    async def on_guild_remove(self, guild):
        """Log quand le bot quitte un serveur"""
        await self.logger.log_guild_remove(guild)

def run_bot():
    """Démarrer le bot"""
    bot = MediaDownloadBot()
    try:
        bot.run(os.getenv('DISCORD_TOKEN'))
    except Exception as e:
        print(f"Failed to start bot: {e}")

if __name__ == "__main__":
    run_bot()