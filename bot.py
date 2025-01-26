import discord
from discord import app_commands
from discord.ext import commands
import os
import io
import re
from datetime import datetime
from dotenv import load_dotenv

# Configuration
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if TOKEN is None:
    raise ValueError("❌ Discord Token not found in .env file")

class MediaDownload(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='/', intents=intents)
        
        # Supported media types
        self.media_types = {
            '📷 images': ['.jpg', '.jpeg', '.png', '.webp'],
            '🎥 videos': ['.mp4', '.mov', '.webm'],
            '🎞️ gifs': ['.gif'],
            '📁 all': []
        }
        self.media_types['📁 all'] = [ext for types in self.media_types.values() for ext in types]

    async def setup_hook(self):
        await self.add_cog(DownloadCog(self))
        print("🔄 Syncing slash commands...")
        try:
            commands = await self.tree.sync()
            print(f"✅ {len(commands)} commands synced!")
        except Exception as e:
            print(f"❌ Error: {e}")

    async def on_ready(self):
        print(f"✅ Logged in as {self.user}")
        print(f"🌐 In {len(self.guilds)} servers")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="/help for commands"
            )
        )

class DownloadCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = 0x2ecc71  # Green

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
            description="Download media files from any channel",
            color=self.color
        )
        
        embed.add_field(
            name="📌 Commands",
            value=(
                "`/download type:[type] number:[number]`\n"
                "Download your selected media files\n\n"
                "**Available types:**\n"
                "• `images` - Download images\n"
                "• `videos` - Download videos\n"
                "• `gifs` - Download GIFs\n"
                "• `all` - Download all media"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 Examples",
            value=(
                "`/download type:images number:50` - Last 50 images\n"
                "`/download type:videos number:All` - All videos\n"
                "`/download type:all number:All` - All media files"
            ),
            inline=False
        )
        
        embed.set_footer(text="Bot created by Arthur")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="download", description="Download specified media")
    @app_commands.choices(
        type=[
            app_commands.Choice(name="Images", value="images"),
            app_commands.Choice(name="Videos", value="videos"),
            app_commands.Choice(name="GIFs", value="gifs"),
            app_commands.Choice(name="All", value="all")
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
    async def download_media(
        self, 
        interaction: discord.Interaction, 
        type: app_commands.Choice[str],
        number: app_commands.Choice[str]
    ):
        # Convert number value
        limit = None if number.value == "-1" else int(number.value)
        
        await interaction.response.send_message("🔍 Searching for media...")
        status_message = await interaction.original_response()
        
        # Clean media type
        clean_type = type.value
        type_key = f"📷 {clean_type}" if clean_type == 'images' else \
                  f"🎥 {clean_type}" if clean_type == 'videos' else \
                  f"🎞️ {clean_type}" if clean_type == 'gifs' else \
                  f"📁 {clean_type}"

        # Initial message
        if limit:
            await status_message.edit(content=f"🔍 Searching in last {limit} messages...")
        else:
            await status_message.edit(content="🔍 Searching in all channel messages...")

        # Collect media
        media_files = []
        total_size = 0
        processed_messages = 0
        
        async with interaction.channel.typing():
            async for message in interaction.channel.history(limit=limit):
                processed_messages += 1
                if processed_messages % 100 == 0:
                    await status_message.edit(content=f"🔍 Searching... ({processed_messages} messages processed)")
                
                for attachment in message.attachments:
                    if self._is_valid_type(attachment.filename, type_key):
                        media_files.append(attachment)
                        total_size += attachment.size

        if not media_files:
            await status_message.edit(content=f"❌ No {clean_type} media found.")
            return

        try:
            # Create scripts
            batch_content = self._create_batch_script(media_files)
            shell_content = self._create_shell_script(media_files)

            # Create thread
            thread_name = f"📥 Download {clean_type}"
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
                description="Choose script based on your system:",
                color=self.color
            )
            
            # Scope description
            scope_desc = f"• Messages processed: {processed_messages}\n"
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
                value="1. Download `download.bat`\n2. Double-click it",
                inline=True
            )
            
            embed.add_field(
                name="🐧 Linux/Mac",
                value="1. Download `download.sh`\n2. `chmod +x download.sh`\n3. `./download.sh`",
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
                description=f"✅ Scripts available in {thread.mention}",
                color=self.color
            )
            await status_message.edit(content=None, embed=embed_status)

        except Exception as e:
            await status_message.edit(content=f"❌ An error occurred: {str(e)}")
            if 'thread' in locals():
                await thread.delete()

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
            # Detect if it's a video or image
            if any(filename.endswith(ext) for ext in ['.mp4', '.mov', '.webm']):
                # Extract category name (before first dash or underscore or space)
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
        script += "explorer .\n"  # Opens folder at the end
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
            # Detect if it's a video or image
            if any(filename.endswith(ext) for ext in ['.mp4', '.mov', '.webm']):
                # Extract category name (before first dash or underscore or space)
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
        script += "xdg-open . 2>/dev/null || open . 2>/dev/null || explorer.exe . 2>/dev/null"  # Opens folder at the end
        return script

    def _is_valid_type(self, filename, type_key):
        """Checks if file matches requested type"""
        ext = os.path.splitext(filename.lower())[1]
        return ext in self.bot.media_types[type_key]

    def _format_size(self, size_bytes):
        """Formats size in readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"

async def main():
    async with MediaDownload() as bot:
        await bot.start(TOKEN)

# Start bot
import asyncio
asyncio.run(main()) 