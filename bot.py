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
from utils.pixeldrain import PixelDrainUploader
from utils.catbox import CatboxUploader

# Configuration
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
LOGS_CHANNEL_ID = os.getenv('LOGS_CHANNEL_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
GOFILE_TOKEN = os.getenv('GOFILE_TOKEN')
TOP_GG_TOKEN = os.getenv('TOP_GG_TOKEN')

# Debug
print("\n=== Debug Discord Bot ===")
print(f"Token exists: {'Yes' if TOKEN else 'No'}")
print(f"Logs Channel ID: {LOGS_CHANNEL_ID}")
print(f"Webhook URL exists: {'Yes' if WEBHOOK_URL else 'No'}")
print("=======================\n")

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
        intents.guilds = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.media_types = {
            'images': ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
            'videos': ['.mp4', '.webm', '.mov'],
            'all': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.webm', '.mov']
        }
        
        # Initialiser les variables de status
        self.last_status = True
        self.log_channel = None
        self.status_task = None

    async def setup_hook(self):
        """Configuration initiale du bot"""
        # Charger les cogs
        await self.load_extension('cogs.download')
        await self.load_extension('cogs.help')
        await self.load_extension('cogs.stats')
        await self.load_extension('cogs.feedback')
        print("✓ All cogs loaded")

    async def on_ready(self):
        """Quand le bot est prêt"""
        print(f"\n=== Bot Ready ===")
        print(f"Logged in as {self.user.name}")
        print(f"Bot ID: {self.user.id}")
        print(f"Guild count: {len(self.guilds)}")
        print("================\n")
        
        # Initialiser le channel de logs
        self.log_channel = self.get_channel(int(os.getenv('LOGS_CHANNEL_ID')))
        if self.log_channel:
            print(f"✓ Log channel found: {self.log_channel.name}")
            
            # Envoyer le message de démarrage
            embed = discord.Embed(
                title="🟢 Bot Online",
                description="Bot has started successfully!",
                color=0x00FF00,
                timestamp=datetime.utcnow()
            )
            await self.log_channel.send(embed=embed)
            
            # Démarrer la tâche de status
            if not self.status_task:
                self.status_task = self.loop.create_task(self.status_check())
        else:
            print("✗ Log channel not found!")

    async def status_check(self):
        """Vérifie périodiquement l'état du bot"""
        await self.wait_until_ready()
        
        while not self.is_closed():
            try:
                if not self.log_channel:
                    self.log_channel = self.get_channel(int(os.getenv('LOGS_CHANNEL_ID')))
                
                if self.log_channel:
                    latency = round(self.latency * 1000)
                    guilds = len(self.guilds)
                    
                    if not self.last_status:  # Si le bot était down avant
                        embed = discord.Embed(
                            title="✅ Bot Recovery",
                            description=(
                                "Bot is back online!\n"
                                f"Latency: {latency}ms\n"
                                f"Servers: {guilds}"
                            ),
                            color=0xFFAA00,
                            timestamp=datetime.utcnow()
                        )
                        await self.log_channel.send(embed=embed)
                    
                    self.last_status = True
                
            except Exception as e:
                if self.last_status:  # Si le bot était up avant
                    try:
                        embed = discord.Embed(
                            title="🔴 Bot Offline",
                            description=f"Bot is experiencing issues\nError: {str(e)}",
                            color=0xFF0000,
                            timestamp=datetime.utcnow()
                        )
                        await self.log_channel.send(embed=embed)
                    except:
                        print(f"Failed to send offline status: {e}")
                    self.last_status = False
            
            await asyncio.sleep(300)  # Check every 5 minutes

    async def on_guild_join(self, guild):
        """Quand le bot rejoint un serveur"""
        if self.log_channel:
            embed = discord.Embed(
                title="📥 Bot Added to Server",
                description=f"Server: {guild.name}\nID: {guild.id}",
                color=0x00FF00,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Members", value=str(guild.member_count))
            embed.add_field(name="Owner", value=str(guild.owner))
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            await self.log_channel.send(embed=embed)

    async def on_guild_remove(self, guild):
        """Quand le bot quitte un serveur"""
        if self.log_channel:
            embed = discord.Embed(
                title="📤 Bot Removed from Server",
                description=f"Server: {guild.name}\nID: {guild.id}",
                color=0xFF0000,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Members", value=str(guild.member_count))
            embed.add_field(name="Owner", value=str(guild.owner))
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            await self.log_channel.send(embed=embed)

def run_bot():
    """Démarrer le bot"""
    bot = MediaDownloadBot()
    try:
        bot.run(os.getenv('DISCORD_TOKEN'))
    except Exception as e:
        print(f"Failed to start bot: {e}")

if __name__ == "__main__":
    run_bot()