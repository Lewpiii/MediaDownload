import discord
from discord.ext import commands
from discord import app_commands
import os
import logging
from datetime import datetime
import tempfile
import zipfile
import aiohttp
from utils.catbox import CatboxUploader

# Configuration
MAX_DISCORD_SIZE = 25 * 1024 * 1024  # 25MB Discord limit
logger = logging.getLogger('bot.download')
logger.setLevel(logging.DEBUG)

class Download(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logger
        self.media_types = {
            'images': ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
            'videos': ['.mp4', '.webm', '.mov'],
            'all': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.webm', '.mov']
        }

    @app_commands.command(
        name="download",
        description="Download media from this channel"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="🖼️ Images", value="images"),
        app_commands.Choice(name="🎥 Videos", value="videos"),
        app_commands.Choice(name="📁 All", value="all")
    ])
    async def download_media(self, interaction: discord.Interaction, type: str, messages: int = 0):
        try:
            await interaction.response.defer(thinking=True)
            logger.debug(f"Starting download with type: {type}, messages: {messages}")

            with tempfile.TemporaryDirectory() as temp_dir:
                downloaded_files = []
                
                # If messages = 0, no limit (None)
                message_limit = None if messages <= 0 else messages
                logger.debug(f"Fetching messages from channel {interaction.channel.name} with limit: {message_limit}")
                
                if message_limit is None:
                    await interaction.followup.send("🔍 Searching through all channel messages... This might take a while.")
                
                try:
                    channel_messages = []
                    async for msg in interaction.channel.history(limit=message_limit):
                        channel_messages.append(msg)
                    logger.debug(f"Successfully fetched {len(channel_messages)} messages")
                    
                    await interaction.followup.send(f"📥 {len(channel_messages)} messages analyzed, processing files...")
                except Exception as e:
                    logger.error(f"Error fetching messages: {e}")
                    await interaction.followup.send("❌ Error while retrieving messages.")
                    return
                
                # Download files
                for message in channel_messages:
                    for attachment in message.attachments:
                        file_ext = os.path.splitext(attachment.filename)[1].lower()
                        if file_ext in self.media_types[type]:
                            async with aiohttp.ClientSession() as session:
                                async with session.get(attachment.url) as response:
                                    if response.status == 200:
                                        file_path = os.path.join(temp_dir, attachment.filename)
                                        with open(file_path, 'wb') as f:
                                            f.write(await response.read())
                                        downloaded_files.append(file_path)

                if not downloaded_files:
                    msg = "❌ No media found"
                    if messages > 0:
                        msg += f" in the last {messages} messages"
                    else:
                        msg += " in the channel"
                    msg += f" of type {type}"
                    await interaction.followup.send(msg)
                    return

                # Create zip
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_name = f"media_{type}_{timestamp}.zip"
                zip_path = os.path.join(temp_dir, zip_name)
                
                with zipfile.ZipFile(zip_path, 'w') as zip_file:
                    for file in downloaded_files:
                        zip_file.write(file, os.path.basename(file))

                # Check zip size
                file_size = os.path.getsize(zip_path)
                logger.debug(f"Zip size: {file_size / (1024*1024):.2f}MB")

                if file_size > MAX_DISCORD_SIZE:
                    # Upload to Catbox
                    logger.debug("File too large, using Catbox")
                    try:
                        uploader = CatboxUploader()
                        with open(zip_path, 'rb') as f:
                            file_data = f.read()
                        url = await uploader.upload_file(filename=zip_name, file_data=file_data)
                        await interaction.followup.send(
                            f"📦 Large file ({file_size / (1024*1024):.2f}MB).\n"
                            f"Download it here: {url}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to upload to Catbox: {e}")
                        await interaction.followup.send(
                            "❌ Error uploading to Catbox. Please try again later."
                        )
                else:
                    # Send directly via Discord
                    logger.debug("Sending file via Discord")
                    await interaction.followup.send(
                        f"📦 {len(downloaded_files)} files found",
                        file=discord.File(zip_path)
                    )

        except Exception as e:
            logger.error(f"Error in download_media: {e}")
            await interaction.followup.send("❌ An error occurred during download.")

async def setup(bot):
    await bot.add_cog(Download(bot)) 