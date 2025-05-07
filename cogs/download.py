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
import psutil
import os.path
import time
from datetime import timedelta

# Configuration
MAX_DISCORD_SIZE = 25 * 1024 * 1024  # 25MB Discord limit
logger = logging.getLogger('bot.download')
logger.setLevel(logging.DEBUG)

class ResourceMonitor:
    def __init__(self, memory_threshold=90, disk_threshold=90):
        self.memory_threshold = memory_threshold  # %
        self.disk_threshold = disk_threshold      # %
        self.start_time = None
        self.processed_items = 0
        self.total_items = 0

    def start_monitoring(self, total_items):
        self.start_time = time.time()
        self.total_items = total_items
        self.processed_items = 0

    def should_pause(self) -> tuple[bool, str]:
        """Check if we should pause processing"""
        mem = self.get_memory_usage()
        disk = self.get_disk_usage()
        
        if mem['percent'] > self.memory_threshold:
            return True, f"Memory usage too high ({mem['percent']:.1f}%)"
        if disk['percent'] > self.disk_threshold:
            return True, f"Disk usage too high ({disk['percent']}%)"
        return False, ""

    def estimate_remaining_time(self) -> str:
        """Calculate estimated time remaining"""
        if not self.start_time or self.processed_items == 0:
            return "Calculating..."
            
        elapsed_time = time.time() - self.start_time
        items_per_second = self.processed_items / elapsed_time
        remaining_items = self.total_items - self.processed_items
        
        if items_per_second > 0:
            seconds_remaining = remaining_items / items_per_second
            return str(timedelta(seconds=int(seconds_remaining)))
        return "Unknown"

    async def process_with_pause(self, interaction, items, process_func):
        """Process items with automatic pausing"""
        self.start_monitoring(len(items))
        
        for item in items:
            should_pause, reason = self.should_pause()
            if should_pause:
                await interaction.followup.send(f"⏸️ Pausing download: {reason}. Waiting 30 seconds...")
                await asyncio.sleep(30)
            
            await process_func(item)
            self.processed_items += 1
            
            if self.processed_items % 5 == 0:
                eta = self.estimate_remaining_time()
                await interaction.followup.send(
                    f"📊 Progress: {self.processed_items}/{self.total_items} "
                    f"({(self.processed_items/self.total_items)*100:.1f}%)\n"
                    f"⏱️ Estimated time remaining: {eta}"
                )

    @staticmethod
    def get_memory_usage():
        process = psutil.Process()
        mem_info = process.memory_info()
        return {
            'rss': mem_info.rss / 1024 / 1024,  # RAM utilisée en MB
            'vms': mem_info.vms / 1024 / 1024,  # Mémoire virtuelle en MB
            'percent': process.memory_percent()
        }
    
    @staticmethod
    def get_disk_usage(path: str = '/tmp'):
        disk = psutil.disk_usage(path)
        return {
            'total': disk.total / 1024 / 1024 / 1024,  # GB
            'used': disk.used / 1024 / 1024 / 1024,
            'free': disk.free / 1024 / 1024 / 1024,
            'percent': disk.percent
        }

    @staticmethod
    def log_resources(logger, path: str = '/tmp'):
        mem = ResourceMonitor.get_memory_usage()
        disk = ResourceMonitor.get_disk_usage(path)
        logger.info(f"Memory: {mem['rss']:.1f}MB (RSS) {mem['percent']:.1f}%")
        logger.info(f"Disk: {disk['free']:.1f}GB free of {disk['total']:.1f}GB ({disk['percent']}% used)")

class Download(commands.Cog):
    """Downloads media files from the channel.
    Use /download to get images, videos, or both from messages.
    Set messages to 0 to search through all channel messages."""

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
        description="Download media from messages (use 0 to search all channel messages)"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="🖼️ Images", value="images"),
        app_commands.Choice(name="🎥 Videos", value="videos"),
        app_commands.Choice(name="📁 All", value="all")
    ])
    @app_commands.describe(
        type="Type of media to download",
        messages="Number of messages to search (use 0 to search ALL messages in the channel)"
    )
    async def download_media(self, interaction: discord.Interaction, type: str, messages: int = 0):
        """
        Download media files from messages.

        Parameters
        ----------
        type: The type of media to download (images, videos, or all)
        messages: Number of recent messages to search (use 0 to search ALL messages in the channel)
        """
        try:
            await interaction.response.defer(thinking=True)
            logger.debug(f"Starting download with type: {type}, messages: {messages}")

            # Initialize resource monitoring
            monitor = ResourceMonitor()
            temp_dir = '/tmp/discord_downloads'
            os.makedirs(temp_dir, exist_ok=True)
            
            # Log initial resources
            monitor.log_resources(logger, temp_dir)
            
            downloaded_files = []
            total_size = 0
            
            message_limit = None if messages <= 0 else messages
            logger.debug(f"Fetching messages from channel {interaction.channel.name} with limit: {message_limit}")
            
            if message_limit is None:
                await interaction.followup.send("🔍 Searching through all channel messages... This might take a while.")
            
            try:
                channel_messages = []
                async for msg in interaction.channel.history(limit=message_limit):
                    channel_messages.append(msg)
                
                total_messages = len(channel_messages)
                logger.debug(f"Successfully fetched {total_messages} messages")
                await interaction.followup.send(f"📥 Found {total_messages} messages, starting media download...")

                # Prepare download function
                async def process_attachment(attachment):
                    nonlocal total_size
                    file_ext = os.path.splitext(attachment.filename)[1].lower()
                    if file_ext in self.media_types[type]:
                        file_path = os.path.join(temp_dir, f"{len(downloaded_files)}_{attachment.filename}")
                        if await self.download_file_in_chunks(attachment.url, file_path):
                            downloaded_files.append(file_path)
                            size = os.path.getsize(file_path)
                            total_size += size
                            logger.debug(f"Downloaded {attachment.filename} ({size/1024/1024:.1f}MB)")

                # Process attachments with monitoring
                await monitor.process_with_pause(interaction, channel_messages, process_attachment)
                
                if not downloaded_files:
                    msg = "❌ No media found"
                    if messages > 0:
                        msg += f" in the last {messages} messages"
                    else:
                        msg += " in the channel"
                    msg += f" of type {type}"
                    await interaction.followup.send(msg)
                    
                    # Cleanup
                    for file in downloaded_files:
                        try:
                            os.remove(file)
                        except:
                            pass
                    return

                # Create zip with progress updates
                await interaction.followup.send("📦 Creating zip file...")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_name = f"media_{type}_{timestamp}.zip"
                zip_path = os.path.join(temp_dir, zip_name)
                
                with zipfile.ZipFile(zip_path, 'w') as zip_file:
                    for i, file in enumerate(downloaded_files):
                        zip_file.write(file, os.path.basename(file))
                        if i % 100 == 0:
                            await interaction.followup.send(
                                f"📦 Zipping files: {i+1}/{len(downloaded_files)}"
                            )

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

            finally:
                # Cleanup
                for file in downloaded_files:
                    try:
                        os.remove(file)
                    except:
                        pass
                try:
                    os.remove(zip_path)
                except:
                    pass

        except Exception as e:
            logger.error(f"Error in download_media: {e}")
            await interaction.followup.send("❌ An error occurred during download.")

    async def download_file_in_chunks(self, url: str, file_path: str, chunk_size: int = 8 * 1024 * 1024):
        """Download a file in chunks and save directly to disk"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(chunk_size):
                            f.write(chunk)
                            downloaded += len(chunk)
                            # Log progress
                            logger.debug(f"Downloaded: {downloaded}/{total_size} bytes ({(downloaded/total_size)*100:.1f}%)")
                    return True
        return False

    async def create_zip_in_chunks(self, files: list, zip_path: str, chunk_size: int = 8 * 1024 * 1024):
        """Create ZIP file in chunks to minimize memory usage"""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in files:
                # Log resources before adding each file
                ResourceMonitor.log_resources(logger)
                
                # Add file to ZIP in chunks
                with open(file_path, 'rb') as f:
                    zf.writestr(os.path.basename(file_path), f.read())
                
                # Remove original file after adding to ZIP
                os.remove(file_path)
                logger.debug(f"Added and removed: {file_path}")

async def setup(bot):
    await bot.add_cog(Download(bot)) 