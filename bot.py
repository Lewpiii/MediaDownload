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

    @app_commands.command(name="botinfo", description="Display bot statistics and information")
    async def botinfo(self, interaction: discord.Interaction):
        try:
            total_users = sum(g.member_count for g in self.bot.guilds)
            total_channels = sum(len(g.channels) for g in self.bot.guilds)
            uptime = datetime.now() - self.bot.start_time
            
            embed = discord.Embed(
                title="ℹ️ Bot Information",
                description="System information and statistics\n━━━━━━━━━━━━━━━━━━━━━━",
                color=self.color
            )
            
            embed.add_field(
                name="📊 General Stats",
                value=f"""
                **Servers:** {len(self.bot.guilds)}
                **Users:** {total_users:,}
                **Channels:** {total_channels:,}
                **Uptime:** {str(uptime).split('.')[0]}
                **Latency:** {round(self.bot.latency * 1000)}ms
                ━━━━━━━━━━━━━━━━
                """,
                inline=False
            )
            
            embed.add_field(
                name="📥 Download Stats",
                value=f"""
                **Total Downloads:** {self.bot.download_count}
                **Successful:** {self.bot.successful_downloads}
                **Failed:** {self.bot.failed_downloads}
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
                inline=False
            )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(
                f"An error occurred: {str(e)}", 
                ephemeral=True
            )

    @app_commands.command(name="download", description="Download media files")
    @app_commands.describe(
        type="Type of media to download",
        number="Number of messages to scan"
    )
    @app_commands.choices(
        type=[
            app_commands.Choice(name="📁 All Files", value="all"),
            app_commands.Choice(name="📷 Images", value="images"),
            app_commands.Choice(name="🎥 Videos", value="videos")
        ],
        number=[
            app_commands.Choice(name="50 messages", value=50),
            app_commands.Choice(name="100 messages", value=100),
            app_commands.Choice(name="500 messages", value=500),
            app_commands.Choice(name="All messages", value=-1)
        ]
    )
    async def download_media(self, interaction: discord.Interaction, 
                           type: app_commands.Choice[str],
                           number: app_commands.Choice[int]):
        await interaction.response.defer()

        try:
            media_files = []
            total_size = 0
            processed = 0
            
            async for msg in interaction.channel.history(limit=number.value):
                processed += 1
                for attachment in msg.attachments:
                    if self._is_valid_type(attachment.filename, type.value):
                        media_files.append(attachment)
                        total_size += attachment.size

            if not media_files:
                await interaction.followup.send(f"No {type.value} files found in the last {number.value} messages.")
                return

            # Create download scripts
            batch_content = self._create_batch_script(media_files)
            shell_content = self._create_shell_script(media_files)

            # Create thread for downloads
            thread = await interaction.channel.create_thread(
                name=f"📥 Download {type.value} ({len(media_files)} files)",
                type=discord.ChannelType.public_thread
            )

            # Send scripts to thread
            await thread.send(
                f"Found {len(media_files)} files in {processed} messages.\n"
                f"Total size: {self._format_size(total_size)}",
                files=[
                    discord.File(io.StringIO(batch_content), "download.bat"),
                    discord.File(io.StringIO(shell_content), "download.sh")
                ]
            )

            # Update stats
            self.bot.download_count += 1
            self.bot.successful_downloads += 1
            self.bot.downloads_by_type[type.value] += 1

            await interaction.followup.send(f"Download ready in {thread.mention}")

        except Exception as e:
            self.bot.download_count += 1
            self.bot.failed_downloads += 1
            await interaction.followup.send(f"An error occurred: {str(e)}")
            if self.bot.logs_channel:
                await self.bot.logs_channel.send(f"Error in download command: {str(e)}")

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
        """Create Windows batch download script"""
        script = "@echo off\n"
        script += "cd %USERPROFILE%\\Desktop\n"
        script += "mkdir MediaDownload 2>nul\n"
        script += "cd MediaDownload\n\n"
        
        for attachment in media_files:
            safe_filename = attachment.filename.replace(" ", "_")
            script += f'curl -L -o "{safe_filename}" "{attachment.url}"\n'
        
        return script

    def _create_shell_script(self, media_files):
        """Create Linux/Mac shell download script"""
        script = "#!/bin/bash\n"
        script += "cd ~/Desktop\n"
        script += "mkdir -p MediaDownload\n"
        script += "cd MediaDownload\n\n"
        
        for attachment in media_files:
            safe_filename = attachment.filename.replace(" ", "_")
            script += f'curl -L -o "{safe_filename}" "{attachment.url}"\n'
        
        return script

bot = MediaDownload()
bot.run(TOKEN)