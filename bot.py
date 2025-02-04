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

# Configuration
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Debug amélioré
print("=== Debug Discord Bot ===")
print(f"Token exists: {'Yes' if TOKEN else 'No'}")
print(f"Token length: {len(TOKEN) if TOKEN else 0}")
print(f"Token first 5 chars: {TOKEN[:5] if TOKEN else 'None'}")
print("=======================")

if not TOKEN:
    raise ValueError("❌ Discord Token not found!")

# List of random English responses to add
RANDOM_RESPONSES = [
    "Poop! 💩",
    "Fart! 💨",
    "Peepee! 🚽",
    "Poopoo! 💩",
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
        
        # Suppression des GIFs des types de médias
        self.media_types = {
            '📷 images': ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'],
            '🎥 videos': ['.mp4', '.mov', '.webm', '.avi', '.mkv', '.flv'],
            '📁 all': []
        }
        self.media_types['📁 all'] = [ext for types in self.media_types.values() for ext in types]

    async def setup_hook(self):
        try:
            await self.add_cog(DownloadCog(self))
            print("✅ DownloadCog chargé avec succès!")
            
            # Synchronisation des commandes
            await self.tree.sync()
            print("✅ Commandes slash synchronisées globalement!")
            
            # Démarrer la tâche de mise à jour du statut
            self.status_update_task = self.loop.create_task(self.change_status())
            print("✅ Status update task started!")
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation: {e}")

    async def change_status(self):
        while not self.is_closed():
            try:
                statuses = [
                    discord.Activity(
                        type=discord.ActivityType.watching,
                        name="/help for commands"
                    ),
                    discord.Activity(
                        type=discord.ActivityType.watching,
                        name=f"{len(self.guilds)} servers"
                    ),
                    discord.Activity(
                        type=discord.ActivityType.watching,
                        name=f"{sum(g.member_count for g in self.guilds)} users"
                    )
                ]
                
                await self.change_presence(activity=statuses[self.status_index])
                self.status_index = (self.status_index + 1) % len(statuses)
                await asyncio.sleep(20)  # Change toutes les 20 secondes
            except Exception as e:
                print(f"Error in change_status: {e}")
                await asyncio.sleep(20)

    async def on_ready(self):
        print(f"✅ Logged in as {self.user}")
        print(f"🌐 In {len(self.guilds)} servers")

    async def close(self):
        if self.status_update_task:
            self.status_update_task.cancel()
        await super().close()

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

class DownloadCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = 0x2ecc71
        self.downloads_in_progress = {}

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
                "• `type` - Select media type (images, videos, gifs, all)\n"
                "• `number` - Number of messages to analyze\n\n"
                "**`/stats`**\n"
                "View bot statistics\n"
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
    @app_commands.choices(
        type=[
            app_commands.Choice(name="📷 Images", value="images"),
            app_commands.Choice(name="🎥 Videos", value="videos"),
            app_commands.Choice(name="📁 All", value="all")
        ],
        number=[
            app_commands.Choice(name="All", value="-1"),
            app_commands.Choice(name="10", value="10"),
            app_commands.Choice(name="50", value="50"),
            app_commands.Choice(name="100", value="100"),
            app_commands.Choice(name="500", value="500"),
            app_commands.Choice(name="1000", value="1000")
        ]
    )
    @app_commands.describe(
        type="Type of media to download",
        number="Number of messages to analyze"
    )
    async def download_media(self, interaction: discord.Interaction, type: app_commands.Choice[str], number: app_commands.Choice[str]):
        try:
            await interaction.response.send_message("🔍 Searching for media...", ephemeral=True)
            status_message = await interaction.original_response()

            type_key = {
                'images': '📷 images',
                'videos': '🎥 videos',
                'all': '📁 all'
            }.get(type.value)

            limit = None if number.value == "-1" else int(number.value)
            
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
                            if self._is_valid_type(attachment.filename, type_key):
                                media_files.append(attachment)
                                total_size += attachment.size
                    
                    except Exception as e:
                        print(f"Erreur lors de l'analyse d'un message: {e}")
                        continue

            if not media_files:
                await status_message.edit(content=f"❌ Aucun {type_key} trouvé dans ce canal.")
                return

            try:
                # Create scripts
                batch_content = self._create_batch_script(media_files)
                shell_content = self._create_shell_script(media_files)

                # Create thread
                thread_name = f"📥 Download {type_key}"
                if limit:
                    thread_name += f" ({limit} messages, {len(media_files)} files)"
                else:
                    thread_name += f" (all messages, {len(media_files)} files)"

                thread = await interaction.channel.create_thread(
                    name=thread_name,
                    type=discord.ChannelType.public_thread
                )

                # Send information
                embed = discord.Embed(
                    title="📥 Download Ready!",
                    description="Choose the script for your operating system:",
                    color=self.color
                )
                
                # Scope description
                scope_desc = f"• Messages scanned: {processed_messages}\n"
                if limit:
                    scope_desc += f"• Limit: {limit} messages\n"
                else:
                    scope_desc += "• Scope: Entire channel\n"

                embed.add_field(
                    name="📊 Summary",
                    value=(
                        scope_desc +
                        f"• Type: {type_key}\n"
                        f"• Files found: {len(media_files)}\n"
                        f"• Total size: {self._format_size(total_size)}"
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="🪟 Windows",
                    value="1. Download `download.bat`\n2. Double-click to run",
                    inline=True
                )
                
                embed.add_field(
                    name="🐧 Linux/Mac",
                    value="1. Download `download.sh`\n2. Run `chmod +x download.sh`\n3. Run `./download.sh`",
                    inline=True
                )

                await thread.send(embed=embed)

                # Send scripts
                await thread.send(
                    "📦 Download scripts:",
                    files=[
                        discord.File(io.BytesIO(batch_content.encode()), "download.bat"),
                        discord.File(io.BytesIO(shell_content.encode()), "download.sh")
                    ]
                )

                # Update status
                embed_status = discord.Embed(
                    description=f"✅ Download ready in {thread.mention}",
                    color=self.color
                )
                await status_message.edit(content=None, embed=embed_status)

            except Exception as e:
                await status_message.edit(content=f"❌ Error: {str(e)}")
                if 'thread' in locals():
                    await thread.delete()

        except Exception as e:
            print(f"Erreur dans download_media: {e}")
            await interaction.followup.send(f"❌ Une erreur est survenue: {str(e)}", ephemeral=True)

    def _create_batch_script(self, media_files):
        """Creates Windows batch script with automatic organization"""
        script = "@echo off\n"
        script += "echo 📥 Downloading and organizing files...\n"
        script += "cd %USERPROFILE%\\Desktop\n"
        script += "mkdir MediaDownload 2>nul\n"
        script += "cd MediaDownload\n"
        script += "mkdir Videos 2>nul\n"
        script += "mkdir Images 2>nul\n\n"

        # Group files by category
        categories = {}
        for attachment in media_files:
            filename = attachment.filename.lower()
            if any(filename.endswith(ext) for ext in ['.mp4', '.mov', '.webm']):
                category = next((
                    word.strip() for word in re.split(r'[-_\s]', filename)
                    if word.strip() and not any(ext in word for ext in ['.mp4', '.mov', '.webm'])
                ), 'others')
                
                if category not in categories:
                    categories[category] = []
                categories[category].append(attachment)

        # Create folders and download files
        total_files = len(media_files)
        current_file = 0

        for category, files in categories.items():
            script += f'mkdir "Videos\\{category}" 2>nul\n'
            for attachment in files:
                current_file += 1
                safe_filename = attachment.filename.replace(" ", "_")
                script += f'echo [{current_file}/{total_files}] {safe_filename}\n'
                script += f'curl -L -o "Videos\\{category}\\{safe_filename}" "{attachment.url}"\n'

        script += "\necho ✅ Download complete!\n"
        script += "echo Files are organized in the MediaDownload folder on your desktop\n"
        script += "explorer .\n"
        script += "pause"
        return script

    def _create_shell_script(self, media_files):
        """Creates Linux/Mac shell script with automatic organization"""
        script = "#!/bin/bash\n"
        script += "echo '📥 Downloading and organizing files...'\n"
        script += "cd ~/Desktop\n"
        script += "mkdir -p MediaDownload\n"
        script += "cd MediaDownload\n"
        script += "mkdir -p Videos Images\n\n"

        # Group files by category
        categories = {}
        for attachment in media_files:
            filename = attachment.filename.lower()
            if any(filename.endswith(ext) for ext in ['.mp4', '.mov', '.webm']):
                category = next((
                    word.strip() for word in re.split(r'[-_\s]', filename)
                    if word.strip() and not any(ext in word for ext in ['.mp4', '.mov', '.webm'])
                ), 'others')
                
                if category not in categories:
                    categories[category] = []
                categories[category].append(attachment)

        # Create folders and download files
        total_files = len(media_files)
        current_file = 0

        for category, files in categories.items():
            script += f'mkdir -p "Videos/{category}"\n'
            for attachment in files:
                current_file += 1
                safe_filename = attachment.filename.replace(" ", "_")
                script += f'echo "[{current_file}/{total_files}] {safe_filename}"\n'
                script += f'curl -L -o "Videos/{category}/{safe_filename}" "{attachment.url}"\n'

        script += "\necho '✅ Download complete!'\n"
        script += "echo 'Files are organized in the MediaDownload folder on your desktop'\n"
        script += "xdg-open . 2>/dev/null || open . 2>/dev/null || explorer.exe . 2>/dev/null"
        return script

    def _is_valid_type(self, filename, type_key):
        """Checks if file matches requested type"""
        ext = os.path.splitext(filename.lower())[1]
        
        # Debug pour voir ce qui est vérifié
        print(f"Vérification fichier: {filename}")
        print(f"Extension: {ext}")
        print(f"Type recherché: {type_key}")
        print(f"Extensions valides: {self.bot.media_types[type_key]}")
        
        return ext in self.bot.media_types[type_key]

    def _format_size(self, size_bytes):
        """Formats size in readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"

    @app_commands.command(name="stats", description="Show bot statistics")
    async def stats(self, interaction: discord.Interaction):
        total_users = sum(g.member_count for g in self.bot.guilds)
        uptime = datetime.now() - self.bot.start_time
        
        embed = discord.Embed(
            title="📊 Bot Statistics",
            color=self.color
        )
        
        embed.add_field(
            name="📈 General",
            value=(
                f"**Servers:** {len(self.bot.guilds)}\n"
                f"**Users:** {total_users:,}\n"
                f"**Uptime:** {str(uptime).split('.')[0]}\n"
                f"**Latency:** {round(self.bot.latency * 1000)}ms"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

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