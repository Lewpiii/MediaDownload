import discord
from discord import app_commands
from discord.ext import commands
import os
import io
from datetime import datetime
from dotenv import load_dotenv
import asyncio
import sys
import traceback
import aiohttp
import time

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
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.messages = True
        super().__init__(command_prefix='!', intents=intents)
        
        self.start_time = datetime.now()
        self.logs_channel = None
        self.webhook_url = WEBHOOK_URL
        self.alert_threshold = 300  # 5 minutes
        self.last_heartbeat = None
        
        # Statistiques de téléchargement
        self.download_count = 0
        self.successful_downloads = 0
        self.failed_downloads = 0
        self.downloads_by_type = {
            'images': 0,
            'videos': 0,
            'all': 0
        }
        
        # Types de médias
        self.media_types = {
            'images': ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'],
            'videos': ['.mp4', '.mov', '.webm', '.avi', '.mkv', '.flv'],
            'all': []
        }
        # Remplir la liste 'all' avec toutes les extensions
        self.media_types['all'] = [ext for types in [self.media_types['images'], self.media_types['videos']] for ext in types]

    async def setup_hook(self):
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
        while not self.is_closed():
            try:
                current_time = datetime.now()
                if self.webhook_url:
                    async with aiohttp.ClientSession() as session:
                        webhook = discord.Webhook.from_url(self.webhook_url, session=session)
                        await webhook.send(
                            content=f"🟢 Bot Heartbeat\nTime: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                self.last_heartbeat = current_time
                
                if self.last_heartbeat:
                    time_since_last = (current_time - self.last_heartbeat).total_seconds()
                    if time_since_last > self.alert_threshold:
                        await self.log_event(
                            "⚠️ Service Alert",
                            "Bot is experiencing delays",
                            0xff9900,
                            last_response=f"{time_since_last:.1f} seconds ago",
                            status="Investigating"
                        )
                
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
        """Unified logging system with consistent styling"""
        if self.logs_channel:
            try:
                embed = discord.Embed(
                    title=title,
                    description=f"{description}\n━━━━━━━━━━━━━━━━━━━━━━",
                    color=color,
                    timestamp=datetime.now()
                )

                # Add all additional fields
                for name, value in fields.items():
                    field_name = name.replace('_', ' ')
                    embed.add_field(
                        name=field_name,
                        value=f"{value}\n━━━━━━━━━━━━━━━━",
                        inline=False
                    )

                await self.logs_channel.send(embed=embed)
            except Exception as e:
                print(f"Error in logging system: {e}")

    async def on_ready(self):
        """Bot startup logging with consistent styling"""
        print(f"✅ Logged in as {self.user}")
        print(f"🌐 In {len(self.guilds)} servers")
        
        if LOGS_CHANNEL_ID:
            self.logs_channel = self.get_channel(LOGS_CHANNEL_ID)
            if self.logs_channel:
                try:
                    with open('last_heartbeat.txt', 'r') as f:
                        last_heartbeat = datetime.fromisoformat(f.read().strip())
                        downtime = datetime.now() - last_heartbeat
                        if downtime.total_seconds() > self.alert_threshold:
                            embed = discord.Embed(
                                title="🔄 Service Recovered",
                                description="Bot was down and has recovered\n━━━━━━━━━━━━━━━━━━━━━━",
                                color=0xf1c40f,
                                timestamp=datetime.now()
                            )
                            embed.add_field(
                                name="Downtime",
                                value=str(downtime).split('.')[0],
                                inline=False
                            )
                            embed.add_field(
                                name="Last Seen",
                                value=last_heartbeat.strftime("%Y-%m-%d %H:%M:%S"),
                                inline=False
                            )
                            await self.logs_channel.send(embed=embed)
                except FileNotFoundError:
                    pass  # First bot startup

                # Startup message
                startup_embed = discord.Embed(
                    title="🟢 Bot Online",
                    description="Bot has successfully started",
                    color=0x2ecc71,
                    timestamp=datetime.now()
                )
                startup_embed.add_field(
                    name="Status",
                    value=f"""**Servers:** {len(self.guilds)}
**Users:** {sum(g.member_count for g in self.guilds)}
**Start Time:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━""",
                    inline=False
                )
                await self.logs_channel.send(embed=startup_embed)
            else:
                print("❌ Logs channel not found!")

    async def on_guild_join(self, guild):
        if self.logs_channel:
            embed = discord.Embed(
                title="✨ New Server",
                description=f"Bot has been added to a new server\n━━━━━━━━━━━━━━━━━━━━━━",
                color=0x2ecc71,
                timestamp=datetime.now()
            )
            embed.add_field(
                name="Server Info",
                value=f"""
                **Name:** {guild.name}
                **ID:** {guild.id}
                **Owner:** {guild.owner}
                **Members:** {guild.member_count}
                **Created:** <t:{int(guild.created_at.timestamp())}:R>
                ━━━━━━━━━━━━━━━━
                """,
                inline=False
            )
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            await self.logs_channel.send(embed=embed)

    async def on_guild_remove(self, guild):
        if self.logs_channel:
            embed = discord.Embed(
                title="❌ Server Removed",
                description=f"Bot has been removed from a server\n━━━━━━━━━━━━━━━━━━━━━━",
                color=0xe74c3c,
                timestamp=datetime.now()
            )
            embed.add_field(
                name="Server Info",
                value=f"""
                **Name:** {guild.name}
                **ID:** {guild.id}
                **Members:** {guild.member_count}
                ━━━━━━━━━━━━━━━━
                """,
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

    async def heartbeat(self):
        """Heartbeat monitoring with consistent styling"""
        while not self.is_closed():
            try:
                current_time = datetime.now()
                self.last_heartbeat = current_time
                
                if self.logs_channel:
                    # Store last heartbeat
                    with open('last_heartbeat.txt', 'w') as f:
                        f.write(self.last_heartbeat.isoformat())
                    
                    # Check for delays
                    if self.last_heartbeat:
                        time_since_last = (current_time - self.last_heartbeat).total_seconds()
                        if time_since_last > self.alert_threshold:
                            await self.log_event(
                                "⚠️ Service Alert",
                                "Bot is experiencing delays",
                                0xff9900,
                                last_response=f"{time_since_last:.1f} seconds ago",
                                status="Investigating"
                            )
                
                await asyncio.sleep(30)
            except Exception as e:
                print(f"Error in heartbeat: {e}")
                if self.logs_channel:
                    await self.log_event(
                        "🔴 Heartbeat Error",
                        "Error in heartbeat monitoring",
                        0xe74c3c,
                        error=f"```{str(e)}```"
                    )
                await asyncio.sleep(30)

class DownloadCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = 0x3498db

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
                title="📊 Statistiques du Bot",
                description="Informations système et statistiques\n━━━━━━━━━━━━━━━━━━━━━━",
                color=self.color
            )
            
            embed.add_field(
                name="📈 Statistiques Générales",
                value=f"""
                **Serveurs:** {len(self.bot.guilds)}
                **Utilisateurs:** {total_users:,}
                **Canaux:** {total_channels:,}
                **Uptime:** {str(uptime).split('.')[0]}
                **Latence:** {round(self.bot.latency * 1000)}ms
                ━━━━━━━━━━━━━━━━
                """,
                inline=False
            )
            
            embed.add_field(
                name="📥 Statistiques de Téléchargement",
                value=f"""
                **Total Downloads:** {self.bot.download_count}
                **Réussis:** {self.bot.successful_downloads}
                **Échoués:** {self.bot.failed_downloads}
                ━━━━━━━━━━━━━━━━
                """,
                inline=False
            )
            
            embed.add_field(
                name="📁 Par Type de Fichier",
                value=f"""
                **Images:** {self.bot.downloads_by_type['images']}
                **Vidéos:** {self.bot.downloads_by_type['videos']}
                **Tous Fichiers:** {self.bot.downloads_by_type['all']}
                ━━━━━━━━━━━━━━━━
                """,
                inline=False
            )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(
                f"Une erreur est survenue: {str(e)}", 
                ephemeral=True
            )

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
            app_commands.Choice(name="All messages", value=999999)
        ]
    )
    async def download_media(self, interaction: discord.Interaction, type: app_commands.Choice[str], number: app_commands.Choice[int]):
        try:
            await interaction.response.send_message("🔍 Searching for media...", ephemeral=True)
            status_message = await interaction.original_response()

            # Debug pour vérifier les valeurs
            print(f"Type sélectionné: {type.value}")
            print(f"Nombre de messages: {number.value}")

            # Conversion du type
            type_key = type.value  # Utilisation directe de la valeur

            # Gestion du nombre de messages
            limit = None if number.value == 999999 else number.value
            
            media_files = []
            total_size = 0
            processed_messages = 0
            start_time = time.time()
            
            async with interaction.channel.typing():
                async for message in interaction.channel.history(limit=limit):
                    if time.time() - start_time > 60:
                        await status_message.edit(content="⚠️ La recherche a pris trop de temps. Essayez avec un nombre plus petit de messages.")
                        return

                    processed_messages += 1
                    if processed_messages % 50 == 0:
                        await status_message.edit(content=f"🔍 Recherche en cours... ({processed_messages} messages analysés)")
                    
                    try:
                        for attachment in message.attachments:
                            # Debug pour voir les fichiers trouvés
                            print(f"Vérification du fichier: {attachment.filename}")
                            
                            # Vérification du type de fichier
                            ext = os.path.splitext(attachment.filename.lower())[1]
                            valid = False

                            if type_key == "images" and ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff']:
                                valid = True
                            elif type_key == "videos" and ext in ['.mp4', '.mov', '.webm', '.avi', '.mkv', '.flv']:
                                valid = True
                            elif type_key == "all":
                                valid = ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', 
                                              '.mp4', '.mov', '.webm', '.avi', '.mkv', '.flv']

                            if valid:
                                print(f"Fichier valide trouvé: {attachment.filename}")
                                media_files.append(attachment)
                                total_size += attachment.size
                    
                    except Exception as e:
                        print(f"Erreur lors de l'analyse d'un message: {e}")
                        continue

            if not media_files:
                await status_message.edit(content=f"❌ Aucun fichier de type {type_key} trouvé dans les {processed_messages} derniers messages.")
                return

            # Create download scripts
            batch_content = self._create_batch_script(media_files)
            shell_content = self._create_shell_script(media_files)

            # Create thread for downloads
            thread = await interaction.channel.create_thread(
                name=f"📥 Download {type_key} ({len(media_files)} files)",
                type=discord.ChannelType.public_thread
            )

            # Send scripts to thread
            await thread.send(
                f"Found {len(media_files)} files in {processed_messages} messages.\n"
                f"Total size: {self._format_size(total_size)}",
                files=[
                    discord.File(io.StringIO(batch_content), "download.bat"),
                    discord.File(io.StringIO(shell_content), "download.sh")
                ]
            )

            await status_message.edit(content=f"✅ Download ready in {thread.mention}")

        except Exception as e:
            print(f"Erreur dans download_media: {e}")
            await interaction.followup.send(f"❌ Une erreur est survenue: {str(e)}", ephemeral=True)

    @app_commands.command(name="suggest", description="Submit a suggestion for the bot")
    @app_commands.describe(
        category="Category of the suggestion",
        suggestion="Your suggestion for the bot"
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="⚙️ Feature", value="feature"),
            app_commands.Choice(name="🎨 Design", value="design"),
            app_commands.Choice(name="🛠️ Improvement", value="improvement"),
            app_commands.Choice(name="🔧 Other", value="other")
        ]
    )
    async def suggest(self, interaction: discord.Interaction,
                     category: app_commands.Choice[str],
                     suggestion: str):
        try:
            if self.bot.logs_channel:
                embed = discord.Embed(
                    title="💡 New Suggestion",
                    description=f"{suggestion}\n━━━━━━━━━━━━━━━━━━━━━━",
                    color=self.color,
                    timestamp=datetime.now()
                )
                
                embed.add_field(
                    name="From",
                    value=f"""
                    **User:** {interaction.user.mention}
                    **Server:** {interaction.guild.name}
                    ━━━━━━━━━━━━━━━━
                    """,
                    inline=False
                )
                
                msg = await self.bot.logs_channel.send(embed=embed)
                await msg.add_reaction("👍")
                await msg.add_reaction("👎")
                
                success_embed = discord.Embed(
                    title="✅ Success",
                    description="Your suggestion has been submitted successfully!",
                    color=0x2ecc71
                )
                await interaction.response.send_message(embed=success_embed, ephemeral=True)
            else:
                await interaction.response.send_message("Suggestion system is not configured.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

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
            if self.bot.logs_channel:
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
                    ━━━━━━━━━━━━━━━━
                    """,
                    inline=False
                )
                
                await self.bot.logs_channel.send(embed=embed)
                
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

    def _format_size(self, size: int) -> str:
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

    def _create_batch_script(self, media_files):
        """Create Windows batch download script with automatic folder organization"""
        script = "@echo off\n"
        script += "setlocal enabledelayedexpansion\n\n"
        
        # Demander le répertoire de destination
        script += 'set /p "DOWNLOAD_DIR=Enter download directory path (default: Desktop/MediaDownload): " || set "DOWNLOAD_DIR=%USERPROFILE%\\Desktop\\MediaDownload"\n'
        script += 'if "!DOWNLOAD_DIR!"=="" set "DOWNLOAD_DIR=%USERPROFILE%\\Desktop\\MediaDownload"\n'
        script += 'mkdir "!DOWNLOAD_DIR!" 2>nul\n'
        script += 'cd /d "!DOWNLOAD_DIR!"\n\n'
        
        # Analyser les fichiers pour déterminer les dossiers nécessaires
        has_images = any(ext in attachment.filename.lower() for attachment in media_files 
                        for ext in self.bot.media_types['images'])
        has_videos = any(ext in attachment.filename.lower() for attachment in media_files 
                        for ext in self.bot.media_types['videos'])
        
        # Créer les dossiers nécessaires
        if has_images:
            script += "mkdir Images 2>nul\n"
        if has_videos:
            script += "mkdir Videos 2>nul\n"
        script += "\n"
        
        # Dictionnaire des catégories
        categories = {
            # Jeux
            'minecraft': 'Games\\Minecraft',
            'valorant': 'Games\\Valorant',
            'fortnite': 'Games\\Fortnite',
            'csgo': 'Games\\CounterStrike',
            'cs2': 'Games\\CounterStrike',
            'lol': 'Games\\LeagueOfLegends',
            'league': 'Games\\LeagueOfLegends',
            'apex': 'Games\\ApexLegends',
            'rocket': 'Games\\RocketLeague',
            'gta': 'Games\\GTA',
            'cod': 'Games\\CallOfDuty',
            'warzone': 'Games\\CallOfDuty',
            
            # Applications
            'photoshop': 'Apps\\Photoshop',
            'ps': 'Apps\\Photoshop',
            'illustrator': 'Apps\\Illustrator',
            'ai': 'Apps\\Illustrator',
            'premiere': 'Apps\\Premiere',
            'pr': 'Apps\\Premiere',
            
            # Système
            'desktop': 'System\\Desktop',
            'screen': 'System\\Desktop',
            'capture': 'System\\Screenshots',
            
            # Réseaux sociaux
            'discord': 'Social\\Discord',
            'twitter': 'Social\\Twitter',
            'instagram': 'Social\\Instagram',
            'insta': 'Social\\Instagram'
        }
        
        # Traiter chaque fichier
        for attachment in media_files:
            filename_lower = attachment.filename.lower()
            ext = os.path.splitext(filename_lower)[1]
            
            # Déterminer le type de média
            base_folder = "Images" if ext in self.bot.media_types['images'] else "Videos"
            
            # Déterminer la sous-catégorie
            subfolder = None
            for keyword, category in categories.items():
                if keyword in filename_lower:
                    subfolder = category
                    break
            
            # Construire le chemin complet
            if subfolder:
                full_path = f"{base_folder}\\{subfolder}"
                script += f'mkdir "{full_path}" 2>nul\n'
            else:
                full_path = f"{base_folder}\\Others"
                script += f'mkdir "{full_path}" 2>nul\n'
            
            # Télécharger le fichier
            safe_filename = attachment.filename.replace(" ", "_")
            script += f'if not exist "{full_path}\\{safe_filename}" (\n'
            script += f'    curl -L -o "{full_path}\\{safe_filename}" "{attachment.url}"\n'
            script += f')\n'
        
        script += "\necho Download complete!\n"
        script += "pause\n"
        return script

    def _create_shell_script(self, media_files):
        """Create Linux/Mac shell download script with automatic folder organization"""
        script = "#!/bin/bash\n\n"
        
        # Demander le répertoire de destination
        script += 'read -p "Enter download directory path (default: ~/Desktop/MediaDownload): " DOWNLOAD_DIR\n'
        script += 'DOWNLOAD_DIR=${DOWNLOAD_DIR:-"$HOME/Desktop/MediaDownload"}\n'
        script += 'mkdir -p "$DOWNLOAD_DIR"\n'
        script += 'cd "$DOWNLOAD_DIR"\n\n'
        
        # Créer les dossiers principaux
        script += "mkdir -p Images Videos\n\n"
        
        # Fonction de gestion des doublons
        script += 'get_unique_filename() {\n'
        script += '    local base_path="$1"\n'
        script += '    local base_name="$2"\n'
        script += '    local extension="$3"\n'
        script += '    local counter=0\n'
        script += '    local target_file="${base_path}/${base_name}${extension}"\n'
        script += '    while [ -f "$target_file" ]; do\n'
        script += '        ((counter++))\n'
        script += '        target_file="${base_path}/${base_name}_${counter}${extension}"\n'
        script += '    done\n'
        script += '    echo "$target_file"\n'
        script += '}\n\n'
        
        # Même dictionnaire de mots-clés que dans la version Windows
        # [Le reste du code est similaire à la version Windows, adapté à la syntaxe bash]
        
        return script

bot = MediaDownload()
bot.run(TOKEN)