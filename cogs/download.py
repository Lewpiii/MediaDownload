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
from utils.topgg_checker import require_vote
import psutil
import os.path
import time
from datetime import timedelta
from pathlib import Path
from config import DOWNLOAD_CONFIG, RESOURCE_LIMITS, MAX_DIRECT_DOWNLOAD_SIZE, MAX_SINGLE_FILE_SIZE, MAX_TOTAL_DOWNLOAD_SIZE
from utils.media_extractor import MediaExtractor

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
            
            # Create progress embed that we'll update
            progress_embed = discord.Embed(
                title="📥 Download in Progress",
                color=0x3498db,
                timestamp=datetime.utcnow()
            )
            progress_embed.add_field(
                name="⚙️ Configuration",
                value=f"**Type**: {media_type.title()}\n**Period**: {date_range}\n**Limit**: {'All messages' if message_limit is None else f'{message_limit} messages'}",
                inline=False
            )
            progress_embed.add_field(
                name="📊 Status",
                value="🔍 Searching messages...",
                inline=False
            )
            progress_embed.set_footer(text="Download is in progress...")
            
            # Update the existing message instead of creating a new one
            await interaction.response.edit_message(embed=progress_embed, view=None)
            
            try:
                # Fetch messages
                channel_messages = []
                async for msg in interaction.channel.history(limit=message_limit):
                    channel_messages.append(msg)
                
                total_messages = len(channel_messages)
                logger.debug(f"Successfully fetched {total_messages} messages")
                
                # Update progress
                progress_embed.set_field_at(
                    1,
                    name="📊 Status",
                    value=f"✅ Found {total_messages} messages\n📥 Downloading media...",
                    inline=False
                )
                await interaction.edit_original_response(embed=progress_embed)

                # Process messages: attachments + embeds (no message content needed)
                failed_downloads = []
                for msg in channel_messages:
                    allowed_exts = self.media_types[media_type]
                    media_list = MediaExtractor.extract(
                        msg,
                        allowed_exts=allowed_exts,
                        include_text_links=False  # keep false to avoid needing message content intent
                    )
                    logger.debug(f"Message {msg.id}: found {len(media_list)} media candidates")

                    for url, suggested_name in media_list:
                        file_ext = os.path.splitext(suggested_name)[1].lower()
                        if file_ext not in allowed_exts:
                            continue

                        file_path = os.path.join(temp_dir, f"{len(downloaded_files)}_{suggested_name}")

                        # Resource pause if necessary
                        should_pause, reason = monitor.should_pause()
                        if should_pause:
                            progress_embed.set_field_at(
                                1,
                                name="📊 Status",
                                value=f"⏸️ Paused: {reason}\nWaiting 30 seconds...",
                                inline=False
                            )
                            await interaction.edit_original_response(embed=progress_embed)
                            await asyncio.sleep(30)

                        # Download with retry logic
                        if await self.download_file_in_chunks(url, file_path):
                            downloaded_files.append(file_path)
                            size = os.path.getsize(file_path)
                            total_size += size
                            logger.debug(f"Downloaded {suggested_name} ({size/1024/1024:.1f}MB)")
                        else:
                            failed_downloads.append(suggested_name)
                            logger.warning(f"Failed to download {suggested_name}")

                        # Update progress every 3 files
                        if len(downloaded_files) % 3 == 0:
                            progress_percent = (len(downloaded_files) / max(1, total_messages)) * 100
                            progress_bar = self._create_progress_bar(progress_percent)
                            status_text = (
                                f"{progress_bar}\n**Files downloaded**: {len(downloaded_files)}\n"
                                f"**Total size**: {total_size/1024/1024:.1f}MB"
                            )
                            if failed_downloads:
                                status_text += f"\n**Failed**: {len(failed_downloads)} files"
                            progress_embed.set_field_at(1, name="📊 Progress", value=status_text, inline=False)
                            await interaction.edit_original_response(embed=progress_embed)
                
                if not downloaded_files:
                    progress_embed.title = "❌ No Media Found"
                    progress_embed.color = 0xFF0000
                    progress_embed.set_field_at(
                        1,
                        name="📊 Result",
                        value=f"No {media_type} files found in the selected period.",
                        inline=False
                    )
                    await interaction.edit_original_response(embed=progress_embed)
                    return

                # Smart organization of files
                progress_embed.set_field_at(
                    1,
                    name="📊 Status",
                    value=f"🧠 Smart organization of {len(downloaded_files)} files...",
                    inline=False
                )
                await interaction.edit_original_response(embed=progress_embed)
                
                organized_files = smart_classifier.organize_with_minimum_threshold(downloaded_files)
                
                # Show organization stats
                stats = smart_classifier.get_organization_stats(organized_files)
                
                # Update embed with organization info
                org_text = f"📁 **{stats['total_files']} files** organized into **{stats['total_categories']} categories**\n\n"
                for category, subcategories in stats['categories'].items():
                    for subcategory, count in subcategories.items():
                        org_text += f"• {category}/{subcategory}: {count} files\n"
                
                progress_embed.set_field_at(
                    1,
                    name="📊 Organization",
                    value=org_text[:1024],  # Discord field limit
                    inline=False
                )
                await interaction.edit_original_response(embed=progress_embed)
                
                # Create organized zip with progress updates
                progress_embed.set_field_at(
                    1,
                    name="📊 Status",
                    value="📦 Creating ZIP file...",
                    inline=False
                )
                await interaction.edit_original_response(embed=progress_embed)
                
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
                                zip_progress = (file_count / total_files) * 100
                                zip_bar = self._create_progress_bar(zip_progress)
                                progress_embed.set_field_at(
                                    1,
                                    name="📊 ZIP Creation",
                                    value=f"{zip_bar}\n**Files compressed**: {file_count}/{total_files}",
                                    inline=False
                                )
                                await interaction.edit_original_response(embed=progress_embed)
                
                # Save classification log
                log_path = os.path.join(temp_dir, f"classification_log_{timestamp}.json")
                smart_classifier.save_classification_log(organized_files, log_path)

                # Check zip size and send result
                file_size = os.path.getsize(zip_path)
                logger.debug(f"Zip size: {file_size / (1024*1024):.2f}MB")

                if file_size > MAX_DIRECT_DOWNLOAD_SIZE:
                    # Upload to Catbox
                    logger.debug("File too large, using Catbox")
                    progress_embed.set_field_at(
                        1,
                        name="📊 Status",
                        value="☁️ Uploading to Catbox (file too large for Discord)...",
                        inline=False
                    )
                    await interaction.edit_original_response(embed=progress_embed)
                    
                    try:
                        uploader = CatboxUploader()
                        with open(zip_path, 'rb') as f:
                            file_data = f.read()
                        url = await uploader.upload_file(filename=zip_name, file_data=file_data)
                        
                        # Final success embed
                        progress_embed.title = "✅ Download Complete!"
                        progress_embed.color = 0x00FF00
                        progress_embed.set_field_at(
                            1,
                            name="📊 Results",
                            value=f"**Files downloaded**: {len(downloaded_files)}\n**Total size**: {file_size / (1024*1024):.2f}MB\n**Organization**: Smart categorized folders\n\n[📥 Click here to download]({url})",
                            inline=False
                        )
                        progress_embed.set_footer(text="Download successful!")
                        await interaction.edit_original_response(embed=progress_embed)
                    except Exception as e:
                        logger.error(f"Failed to upload to Catbox: {e}")
                        progress_embed.title = "❌ Upload Error"
                        progress_embed.color = 0xFF0000
                        progress_embed.set_field_at(
                            1,
                            name="📊 Error",
                            value="Unable to upload the file. Please try again later.",
                            inline=False
                        )
                        await interaction.edit_original_response(embed=progress_embed)
                else:
                    # Send directly via Discord
                    logger.debug("Sending file via Discord")
                    progress_embed.title = "✅ Download Complete!"
                    progress_embed.color = 0x00FF00
                    progress_embed.set_field_at(
                        1,
                        name="📊 Results",
                        value=f"**Files downloaded**: {len(downloaded_files)}\n**Total size**: {file_size / (1024*1024):.2f}MB\n**Organization**: Smart categorized folders\n\n⬇️ ZIP file below",
                        inline=False
                    )
                    progress_embed.set_footer(text="Download successful!")
                    await interaction.edit_original_response(embed=progress_embed, attachments=[discord.File(zip_path)])

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
            try:
                await interaction.edit_original_response(embed=error_embed, view=None)
            except:
                # If editing fails, try to respond
                await interaction.response.send_message(embed=error_embed, ephemeral=True)

    def _create_progress_bar(self, percent: float, length: int = 20) -> str:
        """Create a visual progress bar"""
        filled = int(length * percent / 100)
        bar = "█" * filled + "░" * (length - filled)
        return f"{bar} {percent:.1f}%"
    
    async def download_file_in_chunks(self, url: str, file_path: str, chunk_size: int = None, max_retries: int = 3):
        """Download a file in chunks with timeout handling and retry logic"""
        try:
            # Use smaller chunk size for better reliability
            if chunk_size is None:
                chunk_size = 2 * 1024 * 1024  # 2MB chunks instead of 8MB
                
            # Timeout configuration
            timeout = aiohttp.ClientTimeout(
                total=300,  # 5 minutes total timeout
                connect=30,  # 30 seconds to connect
                sock_read=60  # 60 seconds between reads
            )
            
            for attempt in range(max_retries):
                try:
                    async with aiohttp.ClientSession(timeout=timeout) as session:
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
                                
                                # Stream directly to disk with progress monitoring
                                with open(file_path, 'wb') as f:
                                    last_progress_time = time.time()
                                    
                                    async for chunk in response.content.iter_chunked(chunk_size):
                                        f.write(chunk)
                                        f.flush()  # Force write to disk immediately
                                        downloaded += len(chunk)
                                        
                                        # Check for timeout every chunk
                                        current_time = time.time()
                                        if current_time - last_progress_time > 120:  # 2 minutes without progress
                                            logger.warning(f"Download timeout detected for {url}")
                                            raise aiohttp.ClientTimeout("Download timeout - no progress for 2 minutes")
                                        
                                        last_progress_time = current_time
                                        
                                        # Log progress every 5MB
                                        if downloaded % (5 * 1024 * 1024) == 0:
                                            logger.debug(f"Downloaded: {downloaded}/{total_size} bytes ({(downloaded/total_size)*100:.1f}%)")
                                
                                logger.debug(f"Successfully downloaded {file_path} ({downloaded} bytes)")
                                return True
                            else:
                                logger.error(f"Failed to download {url}: HTTP {response.status}")
                                if attempt < max_retries - 1:
                                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                    continue
                                return False
                                
                except (aiohttp.ClientTimeout, asyncio.TimeoutError) as e:
                    logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries} for {url}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        logger.error(f"All retry attempts failed for {url}")
                        return False
                        
                except Exception as e:
                    logger.error(f"Error on attempt {attempt + 1}/{max_retries} downloading {url}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        return False
                        
        except Exception as e:
            logger.error(f"Critical error downloading {url}: {e}")
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
        name="recover-download",
        description="Recover a stuck download by checking for partial files"
    )
    async def recover_download(self, interaction: discord.Interaction):
        """Recover stuck downloads by checking for partial files"""
        try:
            await interaction.response.defer(thinking=True)
            
            temp_dir = DOWNLOAD_CONFIG['temp_dir']
            if not os.path.exists(temp_dir):
                await interaction.followup.send("❌ No download directory found. No downloads to recover.")
                return
            
            # Find partial files
            partial_files = []
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                if os.path.isfile(file_path) and not filename.endswith('.zip'):
                    file_size = os.path.getsize(file_path)
                    partial_files.append({
                        'name': filename,
                        'size': file_size,
                        'path': file_path
                    })
            
            if not partial_files:
                await interaction.followup.send("✅ No partial downloads found. All downloads are clean.")
                return
            
            # Create recovery embed
            embed = discord.Embed(
                title="🔧 Download Recovery",
                description=f"Found {len(partial_files)} partial files",
                color=0xFFA500,
                timestamp=datetime.utcnow()
            )
            
            # Show partial files
            files_text = ""
            total_size = 0
            for file_info in partial_files[:10]:  # Show first 10
                size_mb = file_info['size'] / (1024 * 1024)
                total_size += file_info['size']
                files_text += f"• {file_info['name']} ({size_mb:.1f}MB)\n"
            
            if len(partial_files) > 10:
                files_text += f"... and {len(partial_files) - 10} more files\n"
            
            embed.add_field(
                name="📁 Partial Files Found",
                value=files_text or "No files found",
                inline=False
            )
            
            embed.add_field(
                name="📊 Summary",
                value=f"**Total files**: {len(partial_files)}\n**Total size**: {total_size / (1024*1024):.1f}MB",
                inline=False
            )
            
            embed.add_field(
                name="🔧 Recovery Options",
                value=(
                    "• **Clean**: Remove all partial files\n"
                    "• **Resume**: Try to complete partial downloads\n"
                    "• **Archive**: Create ZIP from partial files"
                ),
                inline=False
            )
            
            # Create recovery view
            view = RecoveryView(partial_files)
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error in recover_download: {e}")
            await interaction.followup.send("❌ Error during recovery process.")

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

class RecoveryView(discord.ui.View):
    """Recovery options for stuck downloads"""
    
    def __init__(self, partial_files):
        super().__init__(timeout=300)
        self.partial_files = partial_files
    
    @discord.ui.button(label="🧹 Clean All", style=discord.ButtonStyle.danger)
    async def clean_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Remove all partial files"""
        try:
            cleaned_count = 0
            total_size = 0
            
            for file_info in self.partial_files:
                try:
                    file_size = os.path.getsize(file_info['path'])
                    os.remove(file_info['path'])
                    cleaned_count += 1
                    total_size += file_size
                except OSError:
                    pass
            
            embed = discord.Embed(
                title="🧹 Cleanup Complete",
                description=f"Removed {cleaned_count} partial files",
                color=0x00FF00
            )
            embed.add_field(
                name="📊 Cleanup Summary",
                value=f"**Files removed**: {cleaned_count}\n**Space freed**: {total_size / (1024*1024):.1f}MB",
                inline=False
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error during cleanup: {e}", ephemeral=True)
    
    @discord.ui.button(label="📦 Archive Partial", style=discord.ButtonStyle.secondary)
    async def archive_partial(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create ZIP from partial files"""
        try:
            await interaction.response.defer(thinking=True)
            
            temp_dir = DOWNLOAD_CONFIG['temp_dir']
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_name = f"partial_recovery_{timestamp}.zip"
            zip_path = os.path.join(temp_dir, zip_name)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_info in self.partial_files:
                    try:
                        zip_file.write(file_info['path'], file_info['name'])
                    except OSError:
                        pass
            
            file_size = os.path.getsize(zip_path)
            
            embed = discord.Embed(
                title="📦 Archive Created",
                description=f"Created ZIP from {len(self.partial_files)} partial files",
                color=0x00FF00
            )
            embed.add_field(
                name="📊 Archive Info",
                value=f"**Files archived**: {len(self.partial_files)}\n**Archive size**: {file_size / (1024*1024):.1f}MB",
                inline=False
            )
            
            if file_size > MAX_DIRECT_DOWNLOAD_SIZE:
                embed.add_field(
                    name="⚠️ Note",
                    value="File too large for Discord. Uploading to external hosting...",
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                
                # Upload to Catbox
                try:
                    uploader = CatboxUploader()
                    with open(zip_path, 'rb') as f:
                        file_data = f.read()
                    url = await uploader.upload_file(filename=zip_name, file_data=file_data)
                    
                    embed.add_field(
                        name="📥 Download Link",
                        value=f"[Click here to download]({url})",
                        inline=False
                    )
                    await interaction.edit_original_response(embed=embed)
                except Exception as e:
                    await interaction.edit_original_response(
                        embed=discord.Embed(
                            title="❌ Upload Failed",
                            description=f"Could not upload to external hosting: {e}",
                            color=0xFF0000
                        )
                    )
            else:
                await interaction.followup.send(embed=embed, file=discord.File(zip_path))
            
            # Cleanup
            try:
                os.remove(zip_path)
            except OSError:
                pass
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error creating archive: {e}")
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel recovery"""
        embed = discord.Embed(
            title="❌ Recovery Cancelled",
            description="No action taken on partial files.",
            color=0xFF0000
        )
        await interaction.response.edit_message(embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(Download(bot)) 