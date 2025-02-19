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
import aiofiles
import zipfile
from pathlib import Path

# Configuration
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
LOGS_CHANNEL_ID = os.getenv('LOGS_CHANNEL_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

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

class MediaFile:
    def __init__(self, filename, url, size):
        self.filename = filename
        self.url = url
        self.size = size

class MediaDownload(commands.Bot):
    """
    Bot principal pour le téléchargement de médias Discord
    """
    def __init__(self):
        # Configuration des intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.messages = True
        super().__init__(command_prefix='!', intents=intents)
        
        # Initialisation des compteurs et variables
        self._initialize_counters()
        self._initialize_media_types()
        
        # Configuration
        self.start_time = datetime.now()
        self.logs_channel = None
        self.webhook_url = WEBHOOK_URL
        self.alert_threshold = 300  # 5 minutes
        self.last_heartbeat = None
        
    def _initialize_counters(self):
        """Initialise les compteurs de téléchargement"""
        self.download_count = download_count
        self.successful_downloads = successful_downloads
        self.failed_downloads = failed_downloads
        self.downloads_by_type = {
            'images': 0,
            'videos': 0,
            'all': 0
        }
        
    def _initialize_media_types(self):
        """Initialise les types de médias supportés"""
        self.media_types = {
            'images': ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'],
            'videos': ['.mp4', '.mov', '.webm', '.avi', '.mkv', '.flv'],
            'all': []
        }
        # Remplir la liste 'all'
        self.media_types['all'] = [
            ext for types in [
                self.media_types['images'], 
                self.media_types['videos']
            ] for ext in types
        ]

    async def setup_hook(self):
        """Configuration initiale du bot"""
        try:
            await self.add_cog(DownloadCog(self))
            print("✅ Cogs loaded successfully!")
            await self.tree.sync()
            print("✅ Slash commands synced!")
            
            # Démarrer le heartbeat
            self.loop.create_task(self.heartbeat_task())
        except Exception as e:
            print(f"❌ Error during initialization: {e}")

    async def heartbeat_task(self):
        """Tâche de surveillance du heartbeat"""
        while not self.is_closed():
            try:
                current_time = datetime.now()
                
                # Alterner le statut
                if current_time.second % 10 < 5:
                    status_text = f"/help for {len(self.users)} users"
                else:
                    status_text = f"/help for {len(self.guilds)} servers"
                    
                activity = discord.Activity(
                    type=discord.ActivityType.watching, 
                    name=status_text
                )
                await self.change_presence(activity=activity)

                if self.webhook_url:
                    async with aiohttp.ClientSession() as session:
                        webhook = discord.Webhook.from_url(
                            self.webhook_url, 
                            session=session
                        )
                        await webhook.send(
                            content=f"🟢 Bot Heartbeat\nTime: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                self.last_heartbeat = current_time
                
                # Sauvegarder le dernier heartbeat
                with open('last_heartbeat.txt', 'w') as f:
                    f.write(self.last_heartbeat.isoformat())
                
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                print(f"Heartbeat error: {e}")
                await self.log_event(
                    "🔴 Heartbeat Error",
                    "Error in heartbeat monitoring",
                    0xe74c3c,
                    error=f"```{str(e)}```"
                )
                await asyncio.sleep(60)

    async def log_event(self, title: str, description: str, color: int, **fields):
        """Système de logging unifié avec style cohérent"""
        if self.logs_channel:
            try:
                embed = discord.Embed(
                    title=title,
                    description=f"{description}\n━━━━━━━━━━━━━━━━━━━━━━",
                    color=color,
                    timestamp=datetime.now()
                )

                for name, value in fields.items():
                    field_name = name.replace('_', ' ').title()
                    embed.add_field(
                        name=field_name,
                        value=f"{value}\n━━━━━━━━━━━━━━━━",
                        inline=False
                    )

                await self.logs_channel.send(embed=embed)
            except Exception as e:
                print(f"Error in logging system: {e}")

    def save_counters(self):
        """Sauvegarde les compteurs dans un fichier Python"""
        with open('counters.py', 'w') as f:
            f.write(f"download_count = {self.download_count}\n")
            f.write(f"successful_downloads = {self.successful_downloads}\n")
            f.write(f"failed_downloads = {self.failed_downloads}\n")

    async def on_ready(self):
        """Bot startup logging with consistent styling"""
        print(f"\n{'='*50}")
        print(f"✅ Logged in as {self.user}")
        print(f"🌐 Active in {len(self.guilds)} servers")
        print(f"{'='*50}\n")
        
        if LOGS_CHANNEL_ID:
            self.logs_channel = self.get_channel(LOGS_CHANNEL_ID)
            if self.logs_channel:
                try:
                    # Vérification du temps d'arrêt
                    with open('last_heartbeat.txt', 'r') as f:
                        last_heartbeat = datetime.fromisoformat(f.read().strip())
                        downtime = datetime.now() - last_heartbeat
                        if downtime.total_seconds() > self.alert_threshold:
                            recovery_embed = discord.Embed(
                                title="🔄 Service Recovered",
                                description="Bot was offline and has recovered\n━━━━━━━━━━━━━━━━━━━━━━",
                                color=0xf1c40f,
                                timestamp=datetime.now()
                            )
                            recovery_embed.add_field(
                                name="Downtime Duration",
                                value=str(downtime).split('.')[0],
                                inline=False
                            )
                            recovery_embed.add_field(
                                name="Last Active",
                                value=last_heartbeat.strftime("%Y-%m-%d %H:%M:%S"),
                                inline=False
                            )
                            await self.logs_channel.send(embed=recovery_embed)
                except FileNotFoundError:
                    pass  # Premier démarrage du bot

                # Message de démarrage
                startup_embed = discord.Embed(
                    title="🟢 Bot Online",
                    description="Bot successfully initialized and ready",
                    color=0x2ecc71,
                    timestamp=datetime.now()
                )
                
                # Statistiques détaillées
                total_users = sum(g.member_count for g in self.guilds)
                total_channels = sum(len(g.channels) for g in self.guilds)
                
                startup_embed.add_field(
                    name="System Status",
                    value=f"""```yml
Servers    : {len(self.guilds):,}
Users      : {total_users:,}
Channels   : {total_channels:,}
Start Time : {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}```""",
                    inline=False
                )
                
                # Statistiques de téléchargement
                startup_embed.add_field(
                    name="Download Statistics",
                    value=f"""```yml
Total Downloads : {self.download_count:,}
Successful     : {self.successful_downloads:,}
Failed         : {self.failed_downloads:,}```━━━━━━━━━━━━━━━━""",
                    inline=False
                )
                
                await self.logs_channel.send(embed=startup_embed)
            else:
                print("❌ Logs channel not found!")

    async def on_guild_join(self, guild):
        """Logging when bot joins a new server"""
        if self.logs_channel:
            owner = guild.get_member(guild.owner_id)
            owner_name = owner.name if owner else "Unknown"

            embed = discord.Embed(
                title="✨ New Server Added",
                description=f"Bot has been added to a new server\n━━━━━━━━━━━━━━━━━━━━━━",
                color=0x2ecc71,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="Server Information",
                value=f"""```yml
Name        : {guild.name}
ID          : {guild.id}
Owner       : {owner_name}
Owner ID    : {guild.owner_id}
Members     : {guild.member_count:,}
Created     : {guild.created_at.strftime('%Y-%m-%d')}
Channels    : {len(guild.channels)}
Boost Level : {guild.premium_tier}```""",
                inline=False
            )
            
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
                
            embed.add_field(
                name="Updated Bot Stats",
                value=f"""```yml
Total Servers : {len(self.guilds):,}
Total Users   : {sum(g.member_count for g in self.guilds):,}```━━━━━━━━━━━━━━━━""",
                inline=False
            )
            
            await self.logs_channel.send(embed=embed)

    async def on_guild_remove(self, guild):
        """Logging when bot is removed from a server"""
        if self.logs_channel:
            embed = discord.Embed(
                title="❌ Server Removed",
                description=f"Bot has been removed from a server\n━━━━━━━━━━━━━━━━━━━━━━",
                color=0xe74c3c,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="Server Information",
                value=f"""```yml
Name     : {guild.name}
ID       : {guild.id}
Members  : {guild.member_count:,}
Lifetime : {(datetime.now() - guild.created_at).days} days```""",
                inline=False
            )
            
            embed.add_field(
                name="Updated Bot Stats",
                value=f"""```yml
Remaining Servers : {len(self.guilds):,}
Remaining Users  : {sum(g.member_count for g in self.guilds):,}```━━━━━━━━━━━━━━━━""",
                inline=False
            )
            
            await self.logs_channel.send(embed=embed)

    async def send_error_log(self, context: str, error: Exception):
        """Error logging with consistent styling"""
        if self.logs_channel:
            error_traceback = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
            
            await self.log_event(
                "⚠️ Error Occurred",
                f"An error occurred in {context}",
                0xe74c3c,
                error_type=f"`{type(error).__name__}`",
                error_message=f"```py\n{str(error)}\n```",
                traceback=f"```py\n{error_traceback[:1000]}...```" if len(error_traceback) > 1000 else f"```py\n{error_traceback}```"
            )

    async def upload_to_0x0(self, file_path):
        """Upload un fichier sur 0x0.st"""
        try:
            print(f"Starting upload for file: {file_path}")
            url = 'https://0x0.st'
            
            async with aiohttp.ClientSession() as session:
                with open(file_path, 'rb') as f:
                    form_data = aiohttp.FormData()
                    form_data.add_field('file', f, filename=os.path.basename(file_path))
                    
                    async with session.post(url, data=form_data) as response:
                        if response.status == 200:
                            download_link = await response.text()
                            download_link = download_link.strip()  # Enlever les espaces/newlines
                            print(f"Upload successful, link: {download_link}")
                            return download_link
                        else:
                            error_text = await response.text()
                            raise Exception(f"Upload failed with status {response.status}: {error_text}")

    async def upload_to_anonfiles(self, file_path):
        """Upload un fichier sur anonfiles"""
        try:
            print(f"Starting upload for file: {file_path}")
            url = 'https://api.anonfiles.com/upload'
            
            async with aiohttp.ClientSession() as session:
                form_data = aiohttp.FormData()
                form_data.add_field(
                    'file',
                    open(file_path, 'rb'),
                    filename=os.path.basename(file_path)
                )
                
                async with session.post(url, data=form_data) as response:
                    data = await response.json()
                    print(f"Upload response: {data}")
                    
                    if data.get('status'):
                        return data['data']['file']['url']['full']
                    else:
                        raise Exception(f"Upload failed: {data.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"Upload error: {e}")
            raise

class DownloadCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = 0x2b2d31
        # Initialiser le client Top.gg
        self.topgg_token = os.getenv('TOPGG_TOKEN')
        try:
            if self.topgg_token:
                self.topgg_client = topgg.DBLClient(bot, self.topgg_token)
            else:
                print("⚠️ TOPGG_TOKEN non trouvé dans les variables d'environnement")
        except Exception as e:
            print(f"Erreur d'initialisation Top.gg: {e}")
            self.topgg_client = None
        self._last_heartbeat = None
        self._heartbeat_timeout = 30  # secondes
        self.status_text = "🟢 Bot Online"

    async def check_vote(self, user_id: int) -> bool:
        """Vérifie si l'utilisateur a voté"""
        try:
            if self.topgg_client:
                has_voted = await self.topgg_client.get_user_vote(user_id)
                return has_voted
            return False  # Si pas de client Top.gg, on refuse l'accès
        except Exception as e:
            print(f"Erreur Top.gg: {e}")
            return False  # En cas d'erreur, on refuse l'accès

    def _analyze_video_content(self, filename: str) -> str:
        """Analyse le contenu de la vidéo avec l'IA pour déterminer sa catégorie"""
        # Nettoyer le nom du fichier pour l'analyse
        clean_name = filename.lower().replace('_', ' ').replace('-', ' ')
        
        # Demander à Claude d'analyser le nom de la vidéo
        analysis = f"""
        Based on the video filename: "{clean_name}"
        What is the main subject/game/content type? Consider:
        - Game names (Minecraft, Valorant, etc.)
        - Content types (Montage, Gameplay, Tutorial)
        - Specific events (Tournament, Stream Highlights)
        Return just the category name, creating a new one if needed.
        """
        
        # Simuler la réponse de Claude (à remplacer par une vraie API IA plus tard)
        if 'minecraft' in clean_name or 'mc' in clean_name:
            return 'Minecraft'
        elif 'valorant' in clean_name or 'valo' in clean_name:
            return 'Valorant'
        elif 'cs2' in clean_name or 'csgo' in clean_name:
            return 'Counter-Strike'
        elif 'lol' in clean_name or 'league' in clean_name:
            return 'League of Legends'
        elif 'montage' in clean_name:
            return 'Montages'
        elif 'tutorial' in clean_name or 'guide' in clean_name:
            return 'Tutorials'
        elif 'stream' in clean_name or 'live' in clean_name:
            return 'Streams'
        elif 'funny' in clean_name or 'fail' in clean_name:
            return 'Funny Moments'
        else:
            # Analyse plus poussée du contexte
            words = clean_name.split()
            if any(word in words for word in ['kill', 'clutch', 'ace']):
                return 'Highlights'
            elif any(word in words for word in ['gameplay', 'play']):
                return 'Gameplay'
            
            # Si aucune catégorie n'est détectée, créer une nouvelle basée sur les mots significatifs
            significant_words = [w for w in words if len(w) > 3]
            if significant_words:
                return significant_words[0].title()
            
            return 'Other'

    def _create_batch_script(self, media_files):
        """Create Windows batch download script with automatic folder organization"""
        script = """@echo off
chcp 65001 > nul
title Discord Media Downloader
color 0a
mode con: cols=70 lines=30

cls
echo.
echo ====================================
echo      Discord Media Downloader
echo ====================================
echo.

setlocal enabledelayedexpansion

echo [?] Choose download location:
echo ------------------------------------
echo Default: Desktop\MediaDownload
echo Press Enter or type custom path
echo.
set /p "DOWNLOAD_DIR=-> " || set "DOWNLOAD_DIR=%USERPROFILE%\Desktop\MediaDownload"
if "!DOWNLOAD_DIR!"=="" set "DOWNLOAD_DIR=%USERPROFILE%\Desktop\MediaDownload"

echo.
echo [+] Creating directories...
echo.
mkdir "!DOWNLOAD_DIR!" 2>nul
cd /d "!DOWNLOAD_DIR!"

mkdir "Images" 2>nul
mkdir "Videos" 2>nul
"""

        # Analyser d'abord toutes les vidéos et créer une liste des catégories nécessaires
        video_categories = set()
        video_mapping = {}  # Pour stocker la catégorie de chaque vidéo

        # Vérifier l'extension du fichier pour déterminer le type
        def is_video(filename):
            video_extensions = ['.mp4', '.mov', '.webm', '.avi', '.mkv', '.flv']
            return any(filename.lower().endswith(ext) for ext in video_extensions)

        def is_image(filename):
            image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
            return any(filename.lower().endswith(ext) for ext in image_extensions)

        # Analyser et catégoriser les fichiers
        for attachment in media_files.get('all', []):
            filename = attachment.filename
            if is_video(filename):
                category = self._analyze_video_content(filename)
                video_categories.add(category)
                video_mapping[filename] = category

        # Créer uniquement les dossiers nécessaires
        for category in video_categories:
            script += f'mkdir "Videos\\{category}" 2>nul\n'

        script += """
echo [+] Starting downloads...
echo.
"""
        
        # Téléchargement des fichiers
        for attachment in media_files.get('all', []):
            filename = attachment.filename
            safe_filename = filename.replace(" ", "_").replace('"', '')

            if is_video(filename):
                category = video_mapping[filename]
                script += f'echo Downloading video: {safe_filename} to {category}\n'
                script += f'curl.exe -L -o "Videos\\{category}\\{safe_filename}" "{attachment.url}"\n'
            elif is_image(filename):
                script += f'echo Downloading image: {safe_filename}\n'
                script += f'curl.exe -L -o "Images\\{safe_filename}" "{attachment.url}"\n'

        script += """
echo.
echo ====================================
echo          Download Complete!
echo ====================================
echo.
echo [+] Files have been downloaded to: !DOWNLOAD_DIR!
echo.
echo Press any key to exit...
pause >nul
"""
        
        return script

    def _create_shell_script(self, media_files):
        """Create Linux/Mac shell download script with automatic folder organization"""
        script = """#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════
#                    Discord Media Downloader v1.0
#                    Created by: Discord Bot
# ═══════════════════════════════════════════════════════════════════════════

# Configuration des couleurs
RED='\\033[0;31m'
GREEN='\\033[0;32m'
BLUE='\\033[0;34m'
YELLOW='\\033[1;33m'
NC='\\033[0m'

# Afficher le banner
echo
echo -e "${BLUE}  ╔═══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}  ║           Discord Media Downloader            ║${NC}"
echo -e "${BLUE}  ╚═══════════════════════════════════════════════╝${NC}"
echo

# Demander le répertoire de destination
echo -e "${YELLOW}[?]${NC} Enter download directory path"
echo -e "    Default: ~/Desktop/MediaDownload"
read -p "  → " DOWNLOAD_DIR
DOWNLOAD_DIR=${DOWNLOAD_DIR:-"$HOME/Desktop/MediaDownload"}
mkdir -p "$DOWNLOAD_DIR"
cd "$DOWNLOAD_DIR"

# Création des dossiers principaux
echo
echo -e "${BLUE}[+]${NC} Creating directories..."
mkdir -p "Images" && echo -e "${GREEN}[✓]${NC} Created Images folder"
mkdir -p "Videos" && echo -e "${GREEN}[✓]${NC} Created Videos folder"
echo

# Dictionnaire des catégories
declare -A categories=(
    # Games
    ["minecraft"]="Games/Minecraft"
    ["valorant"]="Games/Valorant"
    ["fortnite"]="Games/Fortnite"
    ["csgo"]="Games/CounterStrike"
    ["cs2"]="Games/CounterStrike"
    ["lol"]="Games/LeagueOfLegends"
    ["league"]="Games/LeagueOfLegends"
    ["apex"]="Games/ApexLegends"
    ["rocket"]="Games/RocketLeague"
    ["gta"]="Games/GTA"
    
    # Applications
    ["photoshop"]="Apps/Photoshop"
    ["ps"]="Apps/Photoshop"
    ["illustrator"]="Apps/Illustrator"
    ["ai"]="Apps/Illustrator"
    ["premiere"]="Apps/Premiere"
    ["pr"]="Apps/Premiere"
    
    # System
    ["desktop"]="System/Desktop"
    ["screen"]="System/Screenshots"
    ["capture"]="System/Screenshots"
    
    # Social
    ["discord"]="Social/Discord"
    ["twitter"]="Social/Twitter"
    ["instagram"]="Social/Instagram"
    ["insta"]="Social/Instagram"
)

# Fonction pour obtenir un nom de fichier unique
get_unique_filename() {
    local filepath="$1"
    local directory=$(dirname "$filepath")
    local filename=$(basename "$filepath")
    local base="${filename%.*}"
    local ext="${filename##*.}"
    local counter=1
    local newpath="$filepath"
    
    while [[ -e "$newpath" ]]; do
        newpath="${directory}/${base}_${counter}.${ext}"
        ((counter++))
    done
    
    echo "$newpath"
}

# Fonction de téléchargement avec barre de progression
download_file() {
    local url="$1"
    local output="$2"
    echo -e "${BLUE}[↓]${NC} Downloading: $(basename "$output")"
    curl -L --progress-bar -o "$output" "$url"
    echo -e "${GREEN}[✓]${NC} Downloaded: $(basename "$output")"
}

echo -e "${BLUE}[+]${NC} Starting downloads...\n"
"""

        # Organisation et téléchargement des fichiers
        organized_files = {}
        for attachment in media_files:
            ext = os.path.splitext(attachment.filename.lower())[1]
            file_type = "Images" if ext in self.bot.media_types['images'] else "Videos"
            filename_lower = attachment.filename.lower()
            
            # Déterminer le dossier approprié
            folder_name = "Others"
            for keyword, category in {
                'minecraft': 'Games/Minecraft',
                'valorant': 'Games/Valorant',
                'fortnite': 'Games/Fortnite',
                'csgo': 'Games/CounterStrike',
                'cs2': 'Games/CounterStrike',
                'lol': 'Games/LeagueOfLegends',
                'league': 'Games/LeagueOfLegends',
                'apex': 'Games/ApexLegends',
                'rocket': 'Games/RocketLeague',
                'gta': 'Games/GTA',
            }.items():
                if keyword in filename_lower:
                    folder_name = category
                    break
            
            key = f"{file_type}/{folder_name}"
            if key not in organized_files:
                organized_files[key] = []
            organized_files[key].append(attachment)

        # Générer les commandes de téléchargement
        for folder_path, files in organized_files.items():
            script += f'\n# Creating directory: {folder_path}\n'
            script += f'mkdir -p "{folder_path}"\n'
            
            for attachment in files:
                safe_filename = attachment.filename.replace(" ", "_").replace('"', '\\"')
                script += f'download_file "{attachment.url}" "{folder_path}/{safe_filename}"\n'

        # Message de fin
        script += """
echo
echo -e "${BLUE}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║             Download Complete!                ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════╝${NC}"
echo
echo -e "${GREEN}[✓]${NC} Files have been downloaded to: $DOWNLOAD_DIR"
echo
"""

        return script

    @app_commands.command(name="help", description="Shows bot help")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📥 Media Downloader",
            description="A simple bot to download media files from Discord channels\n━━━━━━━━━━━━━━━━━━━━━━",
            color=self.color
        )
        
        embed.add_field(
            name="📥 Main Commands",
            value="""**`/download`**
Download media files from the current channel
\n• `type` - Select media type (images, videos, all)
• `number` - Number of messages to analyze

**`/stats`**
View bot statistics and download tracking
━━━━━━━━━━━━━━━━""",
            inline=False
        )
        
        embed.add_field(
            name="🛠️ Utility Commands",
            value="""**`/suggest`**
Submit a suggestion for the bot
\n• `category` - Type of suggestion
• `suggestion` - Your detailed suggestion

**`/bug`**
Report a bug or issue
\n• `severity` - How serious the bug is
• `description` - Detailed bug description

**`/help`**
Show this help message
━━━━━━━━━━━━━━━━""",
            inline=False
        )
        
        embed.add_field(
            name="📁 Media Types",
            value="""• `images` - .jpg, .jpeg, .png, .webp, .bmp, .tiff
• `videos` - .mp4, .mov, .webm, .avi, .mkv, .flv
• `all` - All supported formats
━━━━━━━━━━━━━━━━""",
            inline=False
        )
        
        embed.add_field(
            name="💡 Examples",
            value="""• `/download type:📁 All Files number:50`
Download last 50 files

• `/download type:📷 Images number:100`
Download last 100 images

• `/download type:🎥 Videos number:200`
Download last 200 videos
━━━━━━━━━━━━━━━━""",
            inline=False
        )
        
        embed.set_footer(text="Bot created by Arthur • Use /help for commands")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stats", description="Display bot statistics and information")
    async def stats(self, interaction: discord.Interaction):
        try:
            total_users = sum(g.member_count for g in self.bot.guilds)
            total_channels = sum(len(g.channels) for g in self.bot.guilds)
            uptime = datetime.now() - self.bot.start_time
            
            embed = discord.Embed(
                title="📊 Bot Statistics",
                description="System information and statistics\n━━━━━━━━━━━━━━━━━━━━━━",
                color=self.color
            )
            
            # Statistiques système
            system_stats = f"""```yml
Servers    : {len(self.bot.guilds):,}
Users      : {total_users:,}
Channels   : {total_channels:,}
Uptime     : {str(uptime).split('.')[0]}
Latency    : {round(self.bot.latency * 1000)}ms```━━━━━━━━━━━━━━━━"""
            
            embed.add_field(
                name="📈 System Status",
                value=system_stats,
                inline=False
            )
            
            # Statistiques de téléchargement
            success_rate = f"{(self.bot.successful_downloads / self.bot.download_count * 100):.1f}%" if self.bot.download_count > 0 else "N/A"
            download_stats = f"""```yml
Total Downloads : {self.bot.download_count:,}
Successful     : {self.bot.successful_downloads:,}
Failed         : {self.bot.failed_downloads:,}
Success Rate   : {success_rate}```━━━━━━━━━━━━━━━━"""
            
            embed.add_field(
                name="📥 Download Statistics",
                value=download_stats,
                inline=False
            )
            
            # Statistiques par type
            type_stats = f"""```yml
Images : {self.bot.downloads_by_type['images']:,}
Videos : {self.bot.downloads_by_type['videos']:,}
All    : {self.bot.downloads_by_type['all']:,}```━━━━━━━━━━━━━━━━"""
            
            embed.add_field(
                name="📁 Downloads by Type",
                value=type_stats,
                inline=False
            )

            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                f"An error occurred: {str(e)}", 
                ephemeral=True
            )
            await self.bot.send_error_log("stats command", e)

    @app_commands.command(name="download", description="Download media from this channel")
    @app_commands.choices(type=[
        app_commands.Choice(name="🖼️ Images", value="images"),
        app_commands.Choice(name="🎥 Videos", value="videos"),
        app_commands.Choice(name="📁 All", value="all")
    ])
    @app_commands.choices(number=[
        app_commands.Choice(name="Last 10 messages", value=10),
        app_commands.Choice(name="Last 20 messages", value=20),
        app_commands.Choice(name="Last 50 messages", value=50),
        app_commands.Choice(name="All messages", value=0)
    ])
    async def download_media(self, interaction: discord.Interaction, type: app_commands.Choice[str], number: app_commands.Choice[int]):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            files_to_download = []
            limit = None if number.value == 0 else number.value
            
            await interaction.followup.send("🔍 Searching for files...", ephemeral=True)
            
            async for message in interaction.channel.history(limit=limit):
                for attachment in message.attachments:
                    is_image = attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
                    is_video = attachment.filename.lower().endswith(('.mp4', '.webm', '.mov'))
                    
                    if type.value == "all" or \
                       (type.value == "images" and is_image) or \
                       (type.value == "videos" and is_video):
                        files_to_download.append(attachment)

            if not files_to_download:
                await interaction.followup.send("❌ No files found!", ephemeral=True)
                return

            thread = await interaction.channel.create_thread(
                name=f"📥 Download all ({len(files_to_download)} files)",
                auto_archive_duration=60
            )

            status_message = await thread.send("🔄 Preparing your files...")

            with tempfile.TemporaryDirectory() as temp_dir:
                await status_message.edit(content="📥 Downloading files...")
                
                async with aiohttp.ClientSession() as session:
                    for idx, attachment in enumerate(files_to_download, 1):
                        if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                            folder = os.path.join(temp_dir, "Images")
                        else:
                            folder = os.path.join(temp_dir, "Videos")
                            filename = attachment.filename.lower()
                            if "valorant" in filename:
                                folder = os.path.join(temp_dir, "Videos/Valorant")
                            elif "minecraft" in filename:
                                folder = os.path.join(temp_dir, "Videos/Minecraft")
                            elif "fortnite" in filename:
                                folder = os.path.join(temp_dir, "Videos/Fortnite")
                            elif "league" in filename:
                                folder = os.path.join(temp_dir, "Videos/League of Legends")
                            else:
                                folder = os.path.join(temp_dir, "Videos/Other")
                        
                        os.makedirs(folder, exist_ok=True)
                        
                        base_path = os.path.join(folder, attachment.filename)
                        final_path = base_path
                        counter = 1
                        
                        while os.path.exists(final_path):
                            name, ext = os.path.splitext(base_path)
                            final_path = f"{name}_{counter}{ext}"
                            counter += 1

                        async with session.get(attachment.url) as response:
                            if response.status == 200:
                                content = await response.read()
                                with open(final_path, 'wb') as f:
                                    f.write(content)
                        
                        await status_message.edit(
                            content=f"📥 Downloading files... ({idx}/{len(files_to_download)})"
                        )

                await status_message.edit(content="📦 Creating ZIP file...")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_name = f"discord_media_{timestamp}.zip"
                zip_path = os.path.join(temp_dir, zip_name)
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            if file != zip_name:
                                file_path = os.path.join(root, file)
                                arc_name = os.path.relpath(file_path, temp_dir)
                                zip_file.write(file_path, arc_name)

                await status_message.edit(content="☁️ Uploading to cloud...")

                try:
                    # Essayer d'abord 0x0.st
                    try:
                        download_link = await self.upload_to_0x0(zip_path)
                        upload_success = True
                    except Exception as e:
                        print(f"0x0.st upload failed: {e}")
                        # Si 0x0.st échoue, essayer anonfiles
                        try:
                            download_link = await self.upload_to_anonfiles(zip_path)
                            upload_success = True
                        except Exception as e2:
                            print(f"Anonfiles upload failed: {e2}")
                            upload_success = False
                    
                    if upload_success:
                        embed = discord.Embed(
                            title="📥 Download Ready!",
                            description=(
                                f"[Click here to download all files]({download_link})\n\n"
                                f"**Total files:** {len(files_to_download)}\n"
                                f"**Images:** {sum(1 for f in files_to_download if f.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')))}\n"
                                f"**Videos:** {sum(1 for f in files_to_download if f.filename.lower().endswith(('.mp4', '.webm', '.mov')))}\n\n"
                                "⚠️ *Note: Please download the files soon as the link may expire*"
                            ),
                            color=0x00ff00
                        )
                        await status_message.delete()
                        await thread.send(embed=embed)
                    else:
                        raise Exception("All upload methods failed")

                except Exception as upload_error:
                    print(f"All upload attempts failed: {upload_error}")
                    # Si le fichier est trop gros, diviser en parties plus petites
                    if os.path.getsize(zip_path) > 25 * 1024 * 1024:
                        await status_message.edit(content="📦 File is large, splitting into parts...")
                        
                        # Créer un dossier pour les parties
                        parts_dir = os.path.join(temp_dir, "parts")
                        os.makedirs(parts_dir, exist_ok=True)
                        
                        # Diviser le ZIP en parties de 20MB
                        part_size = 20 * 1024 * 1024  # 20MB
                        with open(zip_path, 'rb') as f:
                            part_num = 1
                            while True:
                                data = f.read(part_size)
                                if not data:
                                    break
                                    
                                part_path = os.path.join(parts_dir, f"{zip_name}.part{part_num}")
                                with open(part_path, 'wb') as part_file:
                                    part_file.write(data)
                                part_num += 1
                        
                        # Uploader chaque partie
                        embed = discord.Embed(
                            title="📥 Download Parts",
                            description="The file has been split into multiple parts due to size limitations:",
                            color=0x00ff00
                        )
                        
                        for i in range(1, part_num):
                            part_path = os.path.join(parts_dir, f"{zip_name}.part{i}")
                            try:
                                part_link = await self.upload_to_0x0(part_path)
                                embed.add_field(
                                    name=f"Part {i}/{part_num-1}",
                                    value=f"[Download Part {i}]({part_link})",
                                    inline=False
                                )
                            except Exception as e:
                                embed.add_field(
                                    name=f"Part {i}/{part_num-1}",
                                    value="❌ Upload failed for this part",
                                    inline=False
                                )
                        
                        await status_message.delete()
                        await thread.send(embed=embed)
                    else:
                        await thread.send(
                            "❌ All upload methods failed. Please try again later or contact an administrator."
                        )
                        await status_message.delete()

            await interaction.followup.send(
                f"✅ Process complete! Check thread {thread.mention}",
                ephemeral=True
            )

        except Exception as e:
            print(f"Error: {e}")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)

    @app_commands.command(name="suggest", description="Submit a suggestion for the bot")
    @app_commands.describe(
        category="Category of the suggestion",
        suggestion="Your detailed suggestion"
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="⚙️ Feature", value="feature"),
            app_commands.Choice(name="🎨 Design", value="design"),
            app_commands.Choice(name="🛠️ Improvement", value="improvement"),
            app_commands.Choice(name="🔧 Other", value="other")
        ]
    )
    async def suggest(self, interaction: discord.Interaction, category: app_commands.Choice[str], suggestion: str):
        try:
            embed = discord.Embed(
                title="💡 New Suggestion",
                description=f"A new suggestion has been submitted\n━━━━━━━━━━━━━━━━━━━━━━",
                color=0x3498db,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="Category",
                value=f"```{category.name}```",
                inline=False
            )
            
            embed.add_field(
                name="Suggestion",
                value=f"```{suggestion}```",
                inline=False
            )
            
            embed.add_field(
                name="Submitted by",
                value=f"""```yml
User     : {interaction.user}
User ID  : {interaction.user.id}
Server   : {interaction.guild.name}
Channel  : #{interaction.channel.name}```━━━━━━━━━━━━━━━━""",
                inline=False
            )
            
            await self.bot.logs_channel.send(embed=embed)
            await interaction.response.send_message(
                "✅ Thank you for your suggestion! It has been sent to the developers.",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(
                "❌ An error occurred while submitting your suggestion.",
                ephemeral=True
            )
            await self.bot.send_error_log("suggest command", e)

    @app_commands.command(name="bug", description="Report a bug")
    @app_commands.describe(
        severity="Severity of the bug",
        description="Detailed description of the bug"
    )
    @app_commands.choices(
        severity=[
            app_commands.Choice(name="🟢 Low - Minor issue", value="low"),
            app_commands.Choice(name="🟡 Medium - Affects functionality", value="medium"),
            app_commands.Choice(name="🔴 High - Critical issue", value="high")
        ]
    )
    async def bug(self, interaction: discord.Interaction, 
                 severity: app_commands.Choice[str],
                 description: str):
        try:
            # Changement du canal pour les bugs
            bug_channel = self.bot.get_channel(1338540085515128944)  # Nouveau canal des bugs
            
            if bug_channel:
                embed = discord.Embed(
                    title="🐛 Bug Report",
                    description=f"{description}\n━━━━━━━━━━━━━━━━━━━━━━",
                    color=0xe74c3c,
                    timestamp=datetime.now()
                )
                
                embed.add_field(
                    name="Details",
                    value=f"""
                    **From:** {interaction.user.mention}
                    **User ID:** {interaction.user.id}
                    **Server:** {interaction.guild.name}
                    **Server ID:** {interaction.guild.id}
                    **Severity:** {severity.name}
                    ━━━━━━━━━━━━━━━━
                    """,
                    inline=False
                )
                
                await bug_channel.send(embed=embed)
                
                success_embed = discord.Embed(
                    title="✅ Success",
                    description="Your bug report has been submitted successfully!",
                    color=0x2ecc71
                )
                await interaction.response.send_message(embed=success_embed, ephemeral=True)
            else:
                await interaction.response.send_message("Bug report system is not configured.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

    def _is_valid_type(self, filename: str, type_key: str):
        """Check if file matches requested type"""
        ext = os.path.splitext(filename.lower())[1]
        return ext in self.bot.media_types.get(type_key, [])

    def _format_size(self, size_bytes):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"

    async def check_heartbeat(self):
        """Vérifie l'état du heartbeat"""
        try:
            current_time = time.time()
            if self._last_heartbeat and (current_time - self._last_heartbeat) > self._heartbeat_timeout:
                await self.bot.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.watching,
                        name="🔴 Connection Lost"
                    )
                )
                print(f"Heartbeat missed! Last: {self._last_heartbeat}, Current: {current_time}")
            else:
                await self.bot.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.watching,
                        name=self.status_text
                    )
                )
        except Exception as e:
            print(f"Error in heartbeat check: {e}")

    @tasks.loop(seconds=30)
    async def heartbeat(self):
        """Envoie un heartbeat périodique"""
        try:
            self._last_heartbeat = time.time()
            await self.check_heartbeat()
        except Exception as e:
            print(f"Error in heartbeat: {e}")

    async def send_error_log(self, command_name: str, error: Exception):
        """Log les erreurs dans un canal dédié"""
        print(f"Error in {command_name}: {str(error)}")
        # Vous pouvez ajouter ici un log dans un canal Discord si vous le souhaitez

def setup(bot):
    bot.add_cog(DownloadCog(bot))

# Fonction principale de démarrage
async def main():
    try:
        async with MediaDownload() as bot:
            await bot.start(TOKEN)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()

# Démarrage du bot
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()