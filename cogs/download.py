import discord
from discord.ext import commands
from discord import app_commands
import os
import logging
from datetime import datetime
import tempfile
import zipfile
import aiohttp
import asyncio
from utils.catbox import CatboxUploader
from utils.smart_classifier import smart_classifier
from utils.interactive_menu import InteractiveDownloadMenu
import psutil
import os.path
import time
from datetime import timedelta
from pathlib import Path
from config import DOWNLOAD_CONFIG, RESOURCE_LIMITS, MAX_DIRECT_DOWNLOAD_SIZE, MAX_SINGLE_FILE_SIZE, MAX_TOTAL_DOWNLOAD_SIZE

# Configuration
logger = logging.getLogger('bot.download')
logger.setLevel(logging.DEBUG)

class ResourceMonitor:
    def __init__(self, memory_threshold=None, disk_threshold=None):
        self.memory_threshold = memory_threshold or RESOURCE_LIMITS['memory_threshold']
        self.disk_threshold = disk_threshold or RESOURCE_LIMITS['disk_threshold']
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
    """Downloads media files from the channel with smart organization.
    Use /download to open an interactive menu for easy file downloading.
    Files are automatically organized by category with intelligent folder structure."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logger
        self.media_types = {
            'images': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'],
            'videos': ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv'],
            'all': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv']
        }
        self.interactive_menu = InteractiveDownloadMenu(bot)

    @app_commands.command(
        name="download",
        description="Open interactive download menu with smart file organization"
    )
    async def download_media(self, interaction: discord.Interaction):
        """
        Open interactive download menu for media files.
        
        Features:
        - Interactive button-based interface
        - Date range selection
        - Media type filtering
        - Smart automatic organization
        - Resource monitoring
        """
        try:
            await self.interactive_menu.create_main_menu(interaction)
        except Exception as e:
            logger.error(f"Error in download_media: {e}")
            await interaction.response.send_message("❌ An error occurred while opening the download menu.", ephemeral=True)

    async def start_interactive_download(self, interaction: discord.Interaction, options: dict):
        """Start download process with interactive options"""
        try:
            await interaction.edit_original_response(
                content="🚀 Starting download process...",
                embed=None,
                view=None
            )
            
            # Extract options
            media_type = options.get('media_type', 'all')
            message_limit = options.get('message_limit', 0)
            date_range = options.get('date_range', 'All time')
            
            logger.debug(f"Starting interactive download: {media_type}, limit: {message_limit}, range: {date_range}")
            
            # Initialize resource monitoring
            monitor = ResourceMonitor()
            temp_dir = DOWNLOAD_CONFIG['temp_dir']
            os.makedirs(temp_dir, exist_ok=True)
            
            # Log initial resources
            monitor.log_resources(logger, temp_dir)
            
            downloaded_files = []
            total_size = 0
            
            # Set message limit
            message_limit = None if message_limit <= 0 else message_limit
            
            # Send initial status
            status_embed = discord.Embed(
                title="📥 Download Started",
                description=f"**Media Type**: {media_type.title()}\n**Date Range**: {date_range}\n**Message Limit**: {'All messages' if message_limit is None else f'{message_limit} messages'}",
                color=0x00FF00,
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=status_embed)
            
            if message_limit is None:
                await interaction.followup.send("🔍 Searching through all channel messages... This might take a while.")
            
            try:
                # Fetch messages
                channel_messages = []
                async for msg in interaction.channel.history(limit=message_limit):
                    channel_messages.append(msg)
                
                total_messages = len(channel_messages)
                logger.debug(f"Successfully fetched {total_messages} messages")
                await interaction.followup.send(f"📥 Found {total_messages} messages, starting media download...")

                # Process messages and extract attachments
                for msg in channel_messages:
                    if msg.attachments:
                        for attachment in msg.attachments:
                            file_ext = os.path.splitext(attachment.filename)[1].lower()
                            if file_ext in self.media_types[media_type]:
                                file_path = os.path.join(temp_dir, f"{len(downloaded_files)}_{attachment.filename}")
                                
                                # Check if we should pause due to resource usage
                                should_pause, reason = monitor.should_pause()
                                if should_pause:
                                    await interaction.followup.send(f"⏸️ Pausing download: {reason}. Waiting 30 seconds...")
                                    await asyncio.sleep(30)
                                
                                # Download directly to SSD - NO RAM usage
                                if await self.download_file_in_chunks(attachment.url, file_path):
                                    downloaded_files.append(file_path)
                                    size = os.path.getsize(file_path)
                                    total_size += size
                                    logger.debug(f"Downloaded {attachment.filename} ({size/1024/1024:.1f}MB)")
                                    
                                    # Update progress every 5 files
                                    if len(downloaded_files) % 5 == 0:
                                        eta = monitor.estimate_remaining_time()
                                        progress_embed = discord.Embed(
                                            title="📊 Download Progress",
                                            description=f"**Files Downloaded**: {len(downloaded_files)}\n**Total Size**: {total_size/1024/1024:.1f}MB\n**ETA**: {eta}",
                                            color=0x3498db
                                        )
                                        await interaction.followup.send(embed=progress_embed)
                
                if not downloaded_files:
                    no_files_embed = discord.Embed(
                        title="❌ No Media Found",
                        description=f"No {media_type} files found in the selected range.",
                        color=0xFF0000
                    )
                    await interaction.followup.send(embed=no_files_embed)
                    return

                # Smart organization of files
                await interaction.followup.send("🧠 Organizing files by category...")
                organized_files = smart_classifier.organize_with_minimum_threshold(downloaded_files)
                
                # Show organization stats
                stats = smart_classifier.get_organization_stats(organized_files)
                organization_embed = discord.Embed(
                    title="📁 File Organization",
                    description=f"Organized {stats['total_files']} files into {stats['total_categories']} categories:",
                    color=0x9B59B6
                )
                
                for category, subcategories in stats['categories'].items():
                    category_text = ""
                    for subcategory, count in subcategories.items():
                        category_text += f"• **{subcategory}**: {count} files\n"
                    organization_embed.add_field(
                        name=f"📂 {category}",
                        value=category_text,
                        inline=True
                    )
                
                await interaction.followup.send(embed=organization_embed)
                
                # Create organized zip with progress updates
                await interaction.followup.send("📦 Creating organized zip file...")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_name = f"media_{media_type}_{timestamp}_organized.zip"
                zip_path = os.path.join(temp_dir, zip_name)
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=DOWNLOAD_CONFIG['compress_level']) as zip_file:
                    file_count = 0
                    total_files = len(downloaded_files)
                    
                    for folder_key, file_list in organized_files.items():
                        for file_path in file_list:
                            filename = os.path.basename(file_path)
                            # Create organized path in zip
                            zip_internal_path = f"{folder_key}/{filename}"
                            zip_file.write(file_path, zip_internal_path)
                            
                            file_count += 1
                            if file_count % 10 == 0:
                                await interaction.followup.send(
                                    f"📦 Organizing files: {file_count}/{total_files}"
                                )
                
                # Save classification log
                log_path = os.path.join(temp_dir, f"classification_log_{timestamp}.json")
                smart_classifier.save_classification_log(organized_files, log_path)

                # Check zip size and send result
                file_size = os.path.getsize(zip_path)
                logger.debug(f"Zip size: {file_size / (1024*1024):.2f}MB")

                if file_size > MAX_DIRECT_DOWNLOAD_SIZE:
                    # Upload to Catbox
                    logger.debug("File too large, using Catbox")
                    try:
                        uploader = CatboxUploader()
                        with open(zip_path, 'rb') as f:
                            file_data = f.read()
                        url = await uploader.upload_file(filename=zip_name, file_data=file_data)
                        
                        success_embed = discord.Embed(
                            title="✅ Download Complete!",
                            description=f"**Files Downloaded**: {len(downloaded_files)}\n**Total Size**: {file_size / (1024*1024):.2f}MB\n**Organization**: Smart categorized folders",
                            color=0x00FF00
                        )
                        success_embed.add_field(
                            name="📥 Download Link",
                            value=f"[Click here to download]({url})",
                            inline=False
                        )
                        await interaction.followup.send(embed=success_embed)
                    except Exception as e:
                        logger.error(f"Failed to upload to Catbox: {e}")
                        error_embed = discord.Embed(
                            title="❌ Upload Error",
                            description="Failed to upload large file. Please try again later.",
                            color=0xFF0000
                        )
                        await interaction.followup.send(embed=error_embed)
                else:
                    # Send directly via Discord
                    logger.debug("Sending file via Discord")
                    success_embed = discord.Embed(
                        title="✅ Download Complete!",
                        description=f"**Files Downloaded**: {len(downloaded_files)}\n**Total Size**: {file_size / (1024*1024):.2f}MB\n**Organization**: Smart categorized folders",
                        color=0x00FF00
                    )
                    await interaction.followup.send(embed=success_embed, file=discord.File(zip_path))

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
            logger.error(f"Error in start_interactive_download: {e}")
            error_embed = discord.Embed(
                title="❌ Download Error",
                description="An error occurred during download. Please try again.",
                color=0xFF0000
            )
            await interaction.followup.send(embed=error_embed)

    async def download_file_in_chunks(self, url: str, file_path: str, chunk_size: int = None):
        """Download a file in chunks and save directly to disk (SSD) - NO RAM usage"""
        try:
            # Use configured chunk size
            if chunk_size is None:
                chunk_size = DOWNLOAD_CONFIG['chunk_size']
                
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        total_size = int(response.headers.get('content-length', 0))
                        
                        # Check file size limit
                        if total_size > MAX_SINGLE_FILE_SIZE:
                            logger.warning(f"File too large: {total_size} bytes (max: {MAX_SINGLE_FILE_SIZE})")
                            return False
                            
                        downloaded = 0
                        
                        # Ensure directory exists
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        
                        # Stream directly to disk - NO RAM buffering
                        with open(file_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(chunk_size):
                                f.write(chunk)
                                f.flush()  # Force write to disk immediately
                                downloaded += len(chunk)
                                
                                # Log progress every 10MB
                                if downloaded % (10 * 1024 * 1024) == 0:
                                    logger.debug(f"Downloaded: {downloaded}/{total_size} bytes ({(downloaded/total_size)*100:.1f}%)")
                        
                        logger.debug(f"Successfully downloaded {file_path} ({downloaded} bytes)")
                        return True
                    else:
                        logger.error(f"Failed to download {url}: HTTP {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return False

    async def create_zip_in_chunks(self, files: list, zip_path: str, chunk_size: int = None):
        """Create ZIP file streaming from disk to minimize memory usage"""
        try:
            # Use configured compression level
            compress_level = DOWNLOAD_CONFIG['compress_level']
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=compress_level) as zf:
                for i, file_path in enumerate(files):
                    # Log resources before adding each file
                    ResourceMonitor.log_resources(logger)
                    
                    # Add file to ZIP by streaming from disk - minimal RAM usage
                    with open(file_path, 'rb') as f:
                        zf.writestr(os.path.basename(file_path), f.read())
                    
                    # Remove original file after adding to ZIP to free disk space
                    try:
                        os.remove(file_path)
                        logger.debug(f"Added and removed: {file_path}")
                    except OSError as e:
                        logger.warning(f"Could not remove {file_path}: {e}")
                    
                    # Progress update every 10 files
                    if (i + 1) % 10 == 0:
                        logger.info(f"ZIP progress: {i + 1}/{len(files)} files processed")
                        
        except Exception as e:
            logger.error(f"Error creating ZIP: {e}")
            raise

    @app_commands.command(
        name="test-classification",
        description="Test the smart classification system with sample filenames"
    )
    async def test_classification(self, interaction: discord.Interaction):
        """Test the smart classification system"""
        try:
            await interaction.response.defer(thinking=True)
            
            # Sample filenames for testing
            test_files = [
                "fortnite_victory_royale.mp4",
                "minecraft_build_tutorial.jpg",
                "valorant_spike_defuse.png",
                "discord_screenshot.png",
                "photoshop_edit_final.jpg",
                "random_meme_funny.gif",
                "unknown_file.mp4",
                "another_random.jpg"
            ]
            
            # Test classification
            organized = smart_classifier.organize_with_minimum_threshold(test_files)
            stats = smart_classifier.get_organization_stats(organized)
            
            # Create response embed
            embed = discord.Embed(
                title="🧠 Smart Classification Test",
                description="Testing the intelligent file organization system",
                color=0x00FF00
            )
            
            embed.add_field(
                name="Test Files",
                value=f"```{chr(10).join(test_files)}```",
                inline=False
            )
            
            embed.add_field(
                name="Organization Results",
                value=f"**Total Categories:** {stats['total_categories']}\n**Total Files:** {stats['total_files']}",
                inline=False
            )
            
            # Show detailed organization
            organization_text = ""
            for category, subcategories in stats['categories'].items():
                for subcategory, count in subcategories.items():
                    organization_text += f"📁 **{category}/{subcategory}**: {count} files\n"
            
            embed.add_field(
                name="Folder Structure",
                value=organization_text or "No organization data",
                inline=False
            )
            
            embed.add_field(
                name="Minimum Threshold",
                value=f"Categories need at least **{smart_classifier.minimum_files}** files to be created",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in test_classification: {e}")
            await interaction.followup.send("❌ Error testing classification system.")

async def setup(bot):
    await bot.add_cog(Download(bot)) 