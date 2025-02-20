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
                    status_text = "🤖 Media Downloader"
                else:
                    status_text = f"📊 {len(self.guilds)} servers"
                    
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

    def _create_exe_wrapper(self, batch_content):
        """Create an exe wrapper for the batch script"""
        exe_script = f'''
import os
import sys
import tempfile
import subprocess

def main():
    # Créer un fichier batch temporaire
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bat', mode='w', encoding='utf-8') as f:
        f.write("""{batch_content}""")
        batch_path = f.name
    
    try:
        # Exécuter le batch
        subprocess.run([batch_path], shell=True)
    finally:
        # Nettoyer
        os.unlink(batch_path)

if __name__ == '__main__':
    main()
    '''
        
        return exe_script

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

mkdir Images 2>nul && echo [+] Created Images folder
mkdir Videos 2>nul && echo [+] Created Videos folder
echo.

echo [+] Starting downloads...
echo.
"""
        
        # Téléchargement des fichiers
        for media_type, attachments in media_files.items():
            script += f'mkdir "{media_type}" 2>nul\n'
            script += f'echo [+] Downloading {media_type}...\n'
            
            for attachment in attachments:
                safe_filename = attachment.filename.replace(" ", "_").replace('"', '')
                script += f'echo Downloading: {safe_filename}\n'
                script += f'curl.exe -L -o "{media_type}\\{safe_filename}" "{attachment.url}"\n'
            script += 'echo.\n'
        
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

    @app_commands.command(name="download", description="Download media files")
    @app_commands.choices(
        type=[
            app_commands.Choice(name="📷 Images", value="images"),
            app_commands.Choice(name="🎥 Videos", value="videos"),
            app_commands.Choice(name="📁 All Files", value="all")
        ],
        number=[
            app_commands.Choice(name="50 messages", value=50),
            app_commands.Choice(name="100 messages", value=100),
            app_commands.Choice(name="500 messages", value=500),
            app_commands.Choice(name="1000 messages", value=1000),
            app_commands.Choice(name="All messages", value=0)
        ]
    )
    async def download_media(self, interaction: discord.Interaction, type: app_commands.Choice[str], number: app_commands.Choice[int]):
        try:
            await interaction.response.send_message("🔍 Searching for media...", ephemeral=True)
            status_message = await interaction.original_response()

            try:
                # Vérifier si l'utilisateur a voté
                has_voted = await self.check_vote(interaction.user.id)
                
                # Si l'utilisateur n'a pas voté et demande plus de 50 messages ou tous les fichiers
                if not has_voted and (number.value > 50 or type.value == "all"):
                    embed = discord.Embed(
                        title="⚠️ Vote Required",
                        description=(
                            "You need to vote for the bot to use this feature!\n\n"
                            "📝 **Why vote?**\n"
                            "• Support the bot\n"
                            "• Get access to all features\n"
                            "• Help us grow\n\n"
                            "🔗 **Vote Link**\n"
                            "[Click here to vote](https://top.gg/bot/1332684877551763529/vote)\n\n"
                            "✨ **Free Features**\n"
                            "• Download up to 50 messages\n"
                            "• Download specific media types\n"
                        ),
                        color=0xFF0000
                    )
                    embed.set_footer(text="Your vote lasts 12 hours!")
                    await status_message.edit(embed=embed)
                    return

                # Paramètres de recherche
                type_key = type.value
                limit = None if number.value == 0 else number.value
                
                # Variables de suivi
                media_files = {type_key: []}  # Initialisation avec le type de média comme clé
                total_size = 0
                processed_messages = 0
                start_time = time.time()
                
                # Recherche des médias
                async with interaction.channel.typing():
                    async for message in interaction.channel.history(limit=limit):
                        # Vérification du timeout (5 minutes)
                        if time.time() - start_time > 300:
                            await status_message.edit(content="⚠️ La recherche a pris trop de temps. Essayez avec un nombre plus petit de messages.")
                            return

                        # Mise à jour du statut
                        processed_messages += 1
                        if processed_messages % 100 == 0:
                            await status_message.edit(content=f"🔍 Recherche en cours... ({processed_messages} messages analysés)")
                        
                        # Analyse des pièces jointes
                        for attachment in message.attachments:
                            ext = os.path.splitext(attachment.filename.lower())[1]
                            
                            # Vérification du type de fichier
                            valid = False
                            if type_key == "images" and ext in self.bot.media_types['images']:
                                valid = True
                            elif type_key == "videos" and ext in self.bot.media_types['videos']:
                                valid = True
                            elif type_key == "all" and ext in self.bot.media_types['all']:
                                valid = True

                            if valid:
                                if type_key not in media_files:
                                    media_files[type_key] = []
                                media_files[type_key].append(attachment)
                                total_size += attachment.size

                if not media_files:
                    await status_message.edit(content=f"❌ Aucun fichier de type {type_key} trouvé dans les {processed_messages} derniers messages.")
                    return

                # Création du thread pour les téléchargements
                thread = await interaction.channel.create_thread(
                    name=f"📥 Download {type_key} ({sum(len(files) for files in media_files.values())} files)",
                    type=discord.ChannelType.public_thread,
                    message=status_message  # Associate thread with the status message
                )

                # Message récapitulatif
                summary = (
                    "╔═══════════════════════════════════════════════╗\n"
                    "              Media Download Ready               \n"
                    "╚═══════════════════════════════════════════════╝\n\n"
                    f"📊 **Files Found**\n"
                    f"• Total Files: {sum(len(files) for files in media_files.values())}\n"
                    f"• Messages Analyzed: {processed_messages}\n"
                    f"• Total Size: {self._format_size(total_size)}\n\n"
                    "📥 **Download Instructions**\n"
                    "1. Download `MediaDownloader.bat`\n"
                    "2. Double-click to run\n"
                    "3. Choose download location\n"
                    "4. Wait for completion\n\n"
                    "🛡️ **Security Information**\n"
                    "• Verified Safe Script\n"
                    "• Auto-organizing Downloads\n"
                    "• Smart Folder Structure\n"
                )

                # Création et envoi du script
                batch_content = self._create_batch_script(media_files)

                await thread.send(
                    content=summary,
                    files=[
                        discord.File(
                            io.StringIO(batch_content),
                            filename="MediaDownloader.bat",
                            description="Windows Download Script"
                        )
                    ]
                )

                # Mise à jour des compteurs
                self.bot.download_count += 1
                self.bot.successful_downloads += sum(len(files) for files in media_files.values())
                self.bot.failed_downloads += 0
                self.bot.downloads_by_type[type_key] += sum(len(files) for files in media_files.values())
                self.bot.save_counters()

                # Message de confirmation
                try:
                    await status_message.edit(content=f"✅ Found {sum(len(files) for files in media_files.values())} files! Check the thread for download.")
                except discord.NotFound:
                    await interaction.followup.send(content=f"✅ Found {sum(len(files) for files in media_files.values())} files! Check the thread for download.", ephemeral=True)

            except discord.NotFound:
                # Si l'interaction a expiré, on envoie un nouveau message
                await interaction.followup.send("❌ The interaction has expired. Please try the command again.", ephemeral=True)

        except Exception as e:
            try:
                await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)
            except discord.NotFound:
                print(f"Error in download_media and couldn't send followup: {e}")
            await self.bot.send_error_log("download command", e)

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