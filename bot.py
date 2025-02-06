import discord
from discord import app_commands
from discord.ext import commands
import os
import io
import re
from datetime import datetime
from dotenv import load_dotenv
import random
import time
import asyncio
import sys
import traceback

# Configuration
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
LOGS_CHANNEL_ID = os.getenv('LOGS_CHANNEL_ID')

# Debug amélioré
print("=== Debug Discord Bot ===")
print(f"Token exists: {'Yes' if TOKEN else 'No'}")
print(f"Token length: {len(TOKEN) if TOKEN else 0}")
print(f"Token first 5 chars: {TOKEN[:5] if TOKEN else 'None'}")
print(f"Logs Channel ID: {LOGS_CHANNEL_ID}")
print("=======================")

if not TOKEN:
    raise ValueError("❌ Discord Token not found!")

try:
    LOGS_CHANNEL_ID = int(LOGS_CHANNEL_ID) if LOGS_CHANNEL_ID else None
    if not LOGS_CHANNEL_ID:
        print("⚠️ Warning: Logs Channel ID not set or invalid")
except ValueError as e:
    print(f"❌ Error converting channel IDs: {e}")

# List of random English responses to add
RANDOM_RESPONSES = [
    "Poop! 💩",
    "Fart! 💨",
    "Peepee! 🚽",
    "Poopoo! 💩",
    "...",
    "Making bubbles in my bath! 🛁",
    "Did someone talk about me? *blushes* 😳",
    "Did someone call? 👀",
    "HONK HONK! 🤡",
    "Oops, I've been spotted! 🙈",
    "Hehehe! 😏",
    "Silly human! 🤪"
]

class TenorAttachment:
    def __init__(self, url, filename, size=0):
        self.url = url
        self.filename = filename
        self.size = size

class MediaDownload(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.messages = True
        super().__init__(command_prefix='!', intents=intents)
        self.status_index = 0
        self.status_update_task = None
        self.logs_channel = None
        self.start_time = datetime.now()
        self.heartbeat_task = None
        self.last_heartbeat = None
        self.alert_threshold = 60  # Seuil d'alerte en secondes
        
        # Définition des types de médias avec les emojis
        self.media_types = {
            '📷 images': ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'],
            '🎥 videos': ['.mp4', '.mov', '.webm', '.avi', '.mkv', '.flv'],
            '📁 all': []
        }
        # Remplir la liste 'all' avec toutes les extensions
        self.media_types['📁 all'] = [ext for types in self.media_types.values() for ext in types]

    async def setup_hook(self):
        try:
            await self.add_cog(DownloadCog(self))
            await self.add_cog(UtilsCog(self))
            print("✅ Cogs chargés avec succès!")
            
            # Synchronisation des commandes
            await self.tree.sync()
            print("✅ Commandes slash synchronisées globalement!")
            
            # Démarrer la tâche de mise à jour du statut
            self.status_update_task = self.loop.create_task(self.change_status())
            print("✅ Status update task started!")
            
            # Démarrer la tâche de heartbeat
            self.heartbeat_task = self.loop.create_task(self.heartbeat())
            print("✅ Heartbeat task started!")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation: {e}")

    async def on_ready(self):
        """Bot startup logging with consistent styling"""
        print(f"✅ Logged in as {self.user}")
        print(f"🌐 In {len(self.guilds)} servers")

        if LOGS_CHANNEL_ID:
            try:
                self.logs_channel = self.get_channel(LOGS_CHANNEL_ID)
                if self.logs_channel:
                    # Check for downtime
                    try:
                        with open('last_heartbeat.txt', 'r') as f:
                            last_heartbeat = datetime.fromisoformat(f.read().strip())
                            downtime = datetime.now() - last_heartbeat
                            if downtime.total_seconds() > self.alert_threshold:
                                await self.log_event(
                                    "🔄 Service Recovered",
                                    "Bot was down and has recovered",
                                    0xf1c40f,
                                    Downtime=str(downtime).split('.')[0],
                                    "Last Seen"=last_heartbeat.strftime("%Y-%m-%d %H:%M:%S")
                                )
                    except FileNotFoundError:
                        pass  # First bot startup

                    # Startup message
                    await self.log_event(
                        "🟢 Service Started",
                        "Bot is now online and operational",
                        0x2ecc71,
                        Environment="```\nRender Starter```",
                        Version=f"Discord.py {discord.__version__}",
                        "Start Time"=self.start_time.strftime("%Y-%m-%d %H:%M:%S")
                    )
                else:
                    print("❌ Logs channel not found!")
            except Exception as e:
                print(f"❌ Error in on_ready: {e}")

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
                    embed.add_field(
                        name=name,
                        value=f"{value}\n━━━━━━━━━━━━━━━━",
                        inline=False
                    )

                await self.logs_channel.send(embed=embed)
            except Exception as e:
                print(f"Error in logging system: {e}")

    async def send_error_log(self, context: str, error: Exception):
        """Error logging with consistent styling"""
        if self.logs_channel:
            error_traceback = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
            
            await self.log_event(
                "⚠️ Error Occurred",
                f"An error occurred in {context}",
                0xe74c3c,
                "Error Type"=f"`{type(error).__name__}`",
                "Error Message"=f"```py\n{str(error)}\n```",
                Traceback=f"```py\n{error_traceback[:1000]}...```" if len(error_traceback) > 1000 else f"```py\n{error_traceback}```"
            )

    async def change_status(self):
        """Enhanced dynamic status system"""
        while not self.is_closed():
            try:
                current_time = datetime.now()
                uptime = current_time - self.start_time
                
                statuses = [
                    discord.Activity(
                        type=discord.ActivityType.watching,
                        name=f"/help • {len(self.guilds)} servers"
                    ),
                    discord.Activity(
                        type=discord.ActivityType.watching,
                        name=f"📥 {self.download_count} downloads"
                    ),
                    discord.Activity(
                        type=discord.ActivityType.playing,
                        name=f"with {sum(g.member_count for g in self.guilds)} users"
                    ),
                    discord.Activity(
                        type=discord.ActivityType.watching,
                        name=f"⬆️ Uptime: {str(uptime).split('.')[0]}"
                    ),
                    discord.Activity(
                        type=discord.ActivityType.listening,
                        name=f"🏓 Ping: {round(self.latency * 1000)}ms"
                    )
                ]
                
                await self.change_presence(
                    activity=statuses[self.status_index],
                    status=discord.Status.online
                )
                self.status_index = (self.status_index + 1) % len(statuses)
                await asyncio.sleep(20)
            except Exception as e:
                print(f"Error in change_status: {e}")
                await asyncio.sleep(20)

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
                                "Last Response"=f"{time_since_last:.1f} seconds ago",
                                Status="Investigating"
                            )
                
                await asyncio.sleep(30)
            except Exception as e:
                print(f"Error in heartbeat: {e}")
                if self.logs_channel:
                    await self.log_event(
                        "🔴 Heartbeat Error",
                        "Error in heartbeat monitoring",
                        0xe74c3c,
                        Error=f"```{str(e)}```"
                    )
                await asyncio.sleep(30)

    async def close(self):
        if self.logs_channel:
            try:
                uptime = datetime.now() - self.start_time
                await self.log_event(
                    "🔴 Service Stopped",
                    "Bot is shutting down",
                    0xe74c3c,
                    Uptime=str(uptime).split('.')[0]
                )
            except:
                pass
        if self.status_update_task:
            self.status_update_task.cancel()
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        await super().close()

    async def on_error(self, event, *args, **kwargs):
        error = sys.exc_info()
        await self.send_error_log(f"Event: {event}", error[1])

    async def on_message(self, message):
        # Prevent bot from responding to itself
        if message.author == self.user:
            return

        # Convert message to lowercase for easier detection
        content = message.content.lower()
        
        # List of possible variations
        triggers = ['media download', 'mediadownload', 'media-download']
        
        # Check if any variation is in the message
        if any(trigger in content for trigger in triggers):
            # Choose a random response
            response = random.choice(RANDOM_RESPONSES)
            await message.channel.send(response)

        # Don't forget this line if you have commands in your bot
        await self.process_commands(message)

    async def on_guild_join(self, guild):
        """Server join logging with consistent styling"""
        if self.logs_channel:
            await self.log_event(
                "🎉 Bot Added to New Server",
                f"Bot has been added to {guild.name}",
                0x2ecc71,
                "Server Info"=f"""
                **Name:** {guild.name}
                **ID:** {guild.id}
                **Owner:** {guild.owner}
                **Members:** {guild.member_count}
                **Created:** <t:{int(guild.created_at.timestamp())}:R>
                """,
                Icon=guild.icon.url if guild.icon else "No icon"
            )

    async def on_guild_remove(self, guild):
        """Server leave logging with consistent styling"""
        if self.logs_channel:
            await self.log_event(
                "❌ Bot Removed from Server",
                f"Bot has been removed from {guild.name}",
                0xe74c3c,
                "Server Info"=f"""
                **Name:** {guild.name}
                **ID:** {guild.id}
                **Members:** {guild.member_count}
                """
            )

class DownloadCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = 0x3498db  # Main blue color
        self.error_color = 0xe74c3c  # Error red
        self.success_color = 0x2ecc71  # Success green
        self.warning_color = 0xf1c40f  # Warning yellow
        self.downloads_in_progress = {}
        self.download_count = 0  # Total downloads
        self.successful_downloads = 0  # Successful downloads
        self.failed_downloads = 0  # Failed downloads
        self.downloads_by_type = {
            'images': 0,
            'videos': 0,
            'all': 0
        }

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ {self.bot.user} is ready!")
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="/help for commands"
            )
        )

    @app_commands.command(name="help", description="Shows bot help")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📥 Media Downloader",
            description="A simple bot to download media files from Discord channels\n━━━━━━━━━━━━━━━━━━━━━━",
            color=self.color
        )
        
        embed.add_field(
            name="📥 Main Commands",
            value=(
                "**`/download`**\n"
                "Download media files from the current Discord channel\n"
                "• `type` - Select media type (images, videos, all)\n"
                "• `number` - Number of messages to analyze\n\n"
                "**`/stats`**\n"
                "View download statistics\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            ),
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ Utility Commands",
            value=(
                "**`/botinfo`**\n"
                "Display bot system information\n\n"
                "**`/suggest`**\n"
                "Submit a suggestion for the bot\n\n"
                "**`/bug`**\n"
                "Report a bug\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📁 Media Types for /download",
            value=(
                "• `📷 Images` - .jpg, .jpeg, .png, .webp\n"
                "• `🎥 Videos` - .mp4, .mov, .webm\n"
                "• `📁 All` - All supported formats\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 Examples",
            value=(
                "**Discord Media Download:**\n"
                "• `/download type:images number:50` - Download last 50 images\n"
                "• `/download type:videos number:All` - Download all videos\n"
            ),
            inline=False
        )
        
        embed.set_footer(text="Bot created by Arthur • Use /help for commands")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="download", description="Download media files")
    @app_commands.checks.cooldown(1, 60)
    async def download_media(self, interaction: discord.Interaction, 
        type: app_commands.Choice[str] = app_commands.Choice(name="📁 All", value="📁 all"),
        number: app_commands.Choice[str] = app_commands.Choice(name="50", value="50")):
        
        # Initial progress embed
        progress_embed = discord.Embed(
            title="📥 Download Progress",
            description="Initializing download process...\n━━━━━━━━━━━━━━━━━━━━━━",
            color=self.color
        )
        await interaction.response.send_message(embed=progress_embed)
        message = await interaction.original_response()

        try:
            # Configuration
            limit = None if number.value == "-1" else int(number.value)
            media_files = []
            total_size = 0
            processed_messages = 0
            start_time = time.time()
            
            # Debug
            print(f"Type selected: {type.value}")
            print(f"Media types available: {self.bot.media_types}")
            
            async with interaction.channel.typing():
                async for msg in interaction.channel.history(limit=limit):
                    processed_messages += 1
                    
                    # Process attachments
                    for attachment in msg.attachments:
                        if self._is_valid_type(attachment.filename, type.value):
                            media_files.append(attachment)
                            total_size += attachment.size

            # No files found
            if not media_files:
                no_files_embed = discord.Embed(
                    title="❌ No Files Found",
                    description=f"No {type.value} files found in this channel.\n━━━━━━━━━━━━━━━━━━━━━━",
                    color=self.error_color
                )
                await message.edit(embed=no_files_embed)
                return

            # Create download scripts
            batch_content = self._create_batch_script(media_files)
            shell_content = self._create_shell_script(media_files)

            # Create thread
            thread_name = f"📥 Download {type.value}"
            if limit:
                thread_name += f" ({limit} msgs, {len(media_files)} files)"
            else:
                thread_name += f" (all msgs, {len(media_files)} files)"

            thread = await interaction.channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.public_thread
            )

            # Success message
            success_embed = discord.Embed(
                title="✅ Download Ready",
                description=f"Download scripts are ready in {thread.mention}\n━━━━━━━━━━━━━━━━━━━━━━",
                color=self.success_color
            )
            
            success_embed.add_field(
                name="📊 Summary",
                value=f"""
                **Messages Scanned:** {processed_messages}
                **Files Found:** {len(media_files)}
                **Total Size:** {self._format_size(total_size)}
                **Time Taken:** {time.time() - start_time:.1f}s
                ━━━━━━━━━━━━━━━━
                """,
                inline=False
            )
            
            success_embed.add_field(
                name="📝 Instructions",
                value=f"""
                1. Download the script for your OS
                2. Run it to download all files
                3. Files will be organized by type
                ━━━━━━━━━━━━━━━━
                """,
                inline=False
            )
            
            await message.edit(embed=success_embed)

            # Update stats
            await self.increment_stats(success=True, media_type=type.value)

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}\n━━━━━━━━━━━━━━━━━━━━━━",
                color=self.error_color
            )
            await message.edit(embed=error_embed)
            await self.increment_stats(success=False, media_type=type.value)
            await self.bot.log_event("❌ Error", f"Error in download command: {str(e)}", self.error_color)

    def _create_batch_script(self, media_files):
        """Creates Windows batch script with consistent styling"""
        script = "@echo off\n"
        script += "cls\n"
        script += "echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        script += "echo           Media Downloader Bot\n"
        script += "echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        script += "echo.\n"
        script += "cd %USERPROFILE%\\Desktop\n"
        script += "mkdir MediaDownload 2>nul\n"
        script += "cd MediaDownload\n"
        
        # Create dated folder
        script += "set folder=%date:~6,4%-%date:~3,2%-%date:~0,2%_%time:~0,2%%time:~3,2%\n"
        script += "mkdir \"%folder%\" 2>nul\n"
        script += "cd \"%folder%\"\n"
        
        # Create type folders
        script += "mkdir Videos 2>nul\n"
        script += "mkdir Images 2>nul\n"
        
        # Create info file
        script += "echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ > info.txt\n"
        script += "echo           Download Information >> info.txt\n"
        script += "echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ >> info.txt\n"
        script += f"echo Download Date: %date% %time% >> info.txt\n"
        script += f"echo Total Files: {len(media_files)} >> info.txt\n"
        script += "echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ >> info.txt\n"
        script += "echo File List: >> info.txt\n"
        
        # Download with progress bar
        total_files = len(media_files)
        for i, attachment in enumerate(media_files, 1):
            safe_filename = attachment.filename.replace(" ", "_")
            ext = os.path.splitext(safe_filename)[1].lower()
            
            # Determine folder
            folder = "Videos" if ext in ['.mp4', '.mov', '.webm'] else "Images"
            
            # Progress calculation
            progress = int((i / total_files) * 20)
            progress_bar = "█" * progress + "░" * (20 - progress)
            
            script += f'cls\n'
            script += f'echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            script += f'echo           Downloading Files\n'
            script += f'echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            script += f'echo.\n'
            script += f'echo Progress: [{progress_bar}] {i}/{total_files}\n'
            script += f'echo Current File: {safe_filename}\n'
            script += f'echo.\n'
            script += f'echo {safe_filename} >> info.txt\n'
            script += f'curl -L -o "{folder}\\{safe_filename}" "{attachment.url}"\n'
            script += 'if %errorlevel% neq 0 (\n'
            script += '    echo [ERROR] Failed to download: %safe_filename% >> errors.txt\n'
            script += ')\n'

        script += "\ncls\n"
        script += "echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        script += "echo               Complete!\n"
        script += "echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        script += "echo.\n"
        script += "echo ✓ Download complete!\n"
        script += "echo ✓ Files are organized in dated folders on your desktop\n"
        script += "echo.\n"
        script += "explorer .\n"
        script += "pause"
        return script

    def _create_shell_script(self, media_files):
        """Creates Linux/Mac shell script with consistent styling"""
        script = "#!/bin/bash\n\n"
        script += "clear\n"
        script += "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'\n"
        script += "echo '          Media Downloader Bot'\n"
        script += "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'\n"
        script += "echo\n"
        script += "cd ~/Desktop\n"
        script += "mkdir -p MediaDownload\n"
        script += "cd MediaDownload\n"
        
        # Create dated folder
        script += "folder=$(date '+%Y-%m-%d_%H%M')\n"
        script += "mkdir -p \"$folder\"\n"
        script += "cd \"$folder\"\n"
        
        # Create type folders
        script += "mkdir -p Videos Images\n"
        
        # Create info file
        script += "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' > info.txt\n"
        script += "echo '          Download Information' >> info.txt\n"
        script += "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' >> info.txt\n"
        script += "echo \"Download Date: $(date)\" >> info.txt\n"
        script += f"echo 'Total Files: {len(media_files)}' >> info.txt\n"
        script += "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' >> info.txt\n"
        script += "echo 'File List:' >> info.txt\n"
        
        # Download with progress bar
        total_files = len(media_files)
        for i, attachment in enumerate(media_files, 1):
            safe_filename = attachment.filename.replace(" ", "_")
            ext = os.path.splitext(safe_filename)[1].lower()
            
            # Determine folder
            folder = "Videos" if ext in ['.mp4', '.mov', '.webm'] else "Images"
            
            # Progress calculation
            progress = int((i / total_files) * 20)
            progress_bar = "█" * progress + "░" * (20 - progress)
            
            script += "clear\n"
            script += "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'\n"
            script += "echo '          Downloading Files'\n"
            script += "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'\n"
            script += "echo\n"
            script += f"echo 'Progress: [{progress_bar}] {i}/{total_files}'\n"
            script += f"echo 'Current File: {safe_filename}'\n"
            script += "echo\n"
            script += f"echo '{safe_filename}' >> info.txt\n"
            script += f"curl -L -o \"{folder}/{safe_filename}\" \"{attachment.url}\"\n"
            script += 'if [ $? -ne 0 ]; then\n'
            script += f'    echo "[ERROR] Failed to download: {safe_filename}" >> errors.txt\n'
            script += 'fi\n'

        script += "\nclear\n"
        script += "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'\n"
        script += "echo '              Complete!'\n"
        script += "echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'\n"
        script += "echo\n"
        script += "echo '✓ Download complete!'\n"
        script += "echo '✓ Files are organized in dated folders on your desktop'\n"
        script += "echo\n"
        script += "xdg-open . 2>/dev/null || open . 2>/dev/null || explorer.exe .\n"
        return script

    def _is_valid_type(self, filename: str, type_key: str):
        """Checks if file matches requested type"""
        ext = os.path.splitext(filename.lower())[1]
        
        # Debug
        print(f"Checking file: {filename}")
        print(f"Extension: {ext}")
        print(f"Type requested: {type_key}")
        print(f"Valid extensions: {self.bot.media_types.get(type_key, [])}")
        
        # Make sure type_key exists in media_types
        if type_key not in self.bot.media_types:
            print(f"Invalid type_key: {type_key}")
            return False
            
        return ext in self.bot.media_types[type_key]

    def _format_size(self, size_bytes):
        """Formats size in readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"

    @app_commands.command(name="stats", description="Display download statistics")
    async def stats(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="📊 Download Statistics",
                color=0x2ecc71,
                timestamp=datetime.now()
            )
            
            # Calculate success rate
            if self.download_count > 0:
                success_rate = (self.successful_downloads / self.download_count) * 100
            else:
                success_rate = 0

            embed.add_field(
                name="📈 Downloads",
                value=f"""
                **Total:** {self.download_count}
                **Successful:** {self.successful_downloads}
                **Failed:** {self.failed_downloads}
                **Success Rate:** {success_rate:.1f}%
                """,
                inline=False
            )

            # Stats by media type
            embed.add_field(
                name="📊 By Type",
                value=f"""
                **Images:** {self.downloads_by_type['images']}
                **Videos:** {self.downloads_by_type['videos']}
                **All Files:** {self.downloads_by_type['all']}
                """,
                inline=True
            )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await self.bot.log_event("❌ Error", f"Error in stats command: {str(e)}", 0xe74c3c)
            await interaction.response.send_message("An error occurred.", ephemeral=True)

    async def increment_stats(self, success=True, media_type='all'):
        """Update download statistics"""
        self.download_count += 1
        if success:
            self.successful_downloads += 1
        else:
            self.failed_downloads += 1
            
        # Increment media type counter
        if media_type in self.downloads_by_type:
            self.downloads_by_type[media_type] += 1

class UtilsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = 0x3498db  # Couleur principale bleue
        self.error_color = 0xe74c3c  # Rouge pour les erreurs
        self.success_color = 0x2ecc71  # Vert pour les succès
        self.warning_color = 0xf1c40f  # Jaune pour les avertissements

    @app_commands.command(name="help", description="Shows bot help")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📥 Media Downloader",
            description="A simple bot to download media files from Discord channels\n━━━━━━━━━━━━━━━━━━━━━━",
            color=self.color
        )
        
        embed.add_field(
            name="📥 Main Commands",
            value=(
                "**`/download`**\n"
                "Download media files from the current Discord channel\n"
                "• `type` - Select media type (images, videos, all)\n"
                "• `number` - Number of messages to analyze\n\n"
                "**`/stats`**\n"
                "View download statistics\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            ),
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ Utility Commands",
            value=(
                "**`/botinfo`**\n"
                "Display bot system information\n\n"
                "**`/suggest`**\n"
                "Submit a suggestion for the bot\n\n"
                "**`/bug`**\n"
                "Report a bug\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📁 Media Types for /download",
            value=(
                "• `📷 Images` - .jpg, .jpeg, .png, .webp\n"
                "• `🎥 Videos` - .mp4, .mov, .webm\n"
                "• `📁 All` - All supported formats\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 Examples",
            value=(
                "**Discord Media Download:**\n"
                "• `/download type:images number:50` - Download last 50 images\n"
                "• `/download type:videos number:All` - Download all videos\n"
            ),
            inline=False
        )
        
        embed.set_footer(text="Bot created by Arthur • Use /help for commands")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="botinfo", description="Display bot system information")
    async def botinfo(self, interaction: discord.Interaction):
        try:
            total_users = sum(g.member_count for g in self.bot.guilds)
            total_channels = sum(len(g.channels) for g in self.bot.guilds)
            
            embed = discord.Embed(
                title="ℹ️ Bot Information",
                description="System and performance statistics\n━━━━━━━━━━━━━━━━━━━━━━",
                color=self.color
            )
            
            embed.add_field(
                name="📈 General Stats",
                value=f"""
                **Servers:** {len(self.bot.guilds)}
                **Users:** {total_users:,}
                **Channels:** {total_channels:,}
                ━━━━━━━━━━━━━━━━
                """,
                inline=True
            )
            
            embed.add_field(
                name="⚙️ Performance",
                value=f"""
                **Latency:** {round(self.bot.latency * 1000)}ms
                **Uptime:** {str(datetime.now() - self.bot.start_time).split('.')[0]}
                **Version:** {discord.__version__}
                ━━━━━━━━━━━━━━━━
                """,
                inline=True
            )
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await self.error_response(interaction, str(e))

    @app_commands.command(name="stats", description="Display download statistics")
    async def stats(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="📊 Download Statistics",
                description="Media download tracking and analytics\n━━━━━━━━━━━━━━━━━━━━━━",
                color=self.color
            )
            
            # Calculate success rate
            if self.bot.download_count > 0:
                success_rate = (self.bot.successful_downloads / self.bot.download_count) * 100
            else:
                success_rate = 0

            embed.add_field(
                name="📈 Download Stats",
                value=f"""
                **Total:** {self.bot.download_count}
                **Successful:** {self.bot.successful_downloads}
                **Failed:** {self.bot.failed_downloads}
                **Success Rate:** {success_rate:.1f}%
                ━━━━━━━━━━━━━━━━
                """,
                inline=False
            )

            embed.add_field(
                name="📁 By File Type",
                value=f"""
                **Images:** {self.bot.downloads_by_type['images']}
                **Videos:** {self.bot.downloads_by_type['videos']}
                **All Files:** {self.bot.downloads_by_type['all']}
                ━━━━━━━━━━━━━━━━
                """,
                inline=True
            )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await self.error_response(interaction, str(e))

    @app_commands.command(name="suggest", description="Submit a suggestion for the bot")
    async def suggest(self, interaction: discord.Interaction, suggestion: str):
        try:
            if self.bot.logs_channel:
                embed = discord.Embed(
                    title="💡 New Suggestion",
                    description=f"{suggestion}\n━━━━━━━━━━━━━━━━━━━━━━",
                    color=self.color
                )
                embed.add_field(
                    name="📝 Details",
                    value=f"""
                    **From:** {interaction.user.mention}
                    **User ID:** {interaction.user.id}
                    **Server:** {interaction.guild.name}
                    **Server ID:** {interaction.guild.id}
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
                    color=self.success_color
                )
                await interaction.response.send_message(embed=success_embed, ephemeral=True)
            else:
                await self.error_response(interaction, "Suggestion system is not configured.")
        except Exception as e:
            await self.error_response(interaction, str(e))

    @app_commands.command(name="bug", description="Report a bug")
    async def report_bug(self, interaction: discord.Interaction, description: str):
        try:
            if self.bot.logs_channel:
                embed = discord.Embed(
                    title="🐛 Bug Report",
                    description=f"{description}\n━━━━━━━━━━━━━━━━━━━━━━",
                    color=self.warning_color
                )
                embed.add_field(
                    name="📝 Details",
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
                    color=self.success_color
                )
                await interaction.response.send_message(embed=success_embed, ephemeral=True)
            else:
                await self.error_response(interaction, "Bug report system is not configured.")
        except Exception as e:
            await self.error_response(interaction, str(e))

    async def error_response(self, interaction: discord.Interaction, error_message: str):
        """Unified error response method"""
        error_embed = discord.Embed(
            title="❌ Error",
            description=f"{error_message}\n━━━━━━━━━━━━━━━━━━━━━━",
            color=self.error_color
        )
        try:
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send(embed=error_embed, ephemeral=True)

async def main():
    try:
        bot = MediaDownload()
        bot.start_time = datetime.now()
        async with bot:
            print("🚀 Starting bot...")
            await bot.start(TOKEN)
    except discord.errors.LoginFailure as e:
        print(f"❌ Login Failed: {str(e)}")
        print("⚠️ Please check if your token is valid")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

# Start bot
asyncio.run(main()) 