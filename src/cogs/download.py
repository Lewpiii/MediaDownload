import discord
from discord.ext import commands
from discord import app_commands
import os
import logging
from datetime import datetime
import asyncio
import re

# Relative imports from src
from ..utils.catbox import CatboxUploader
from ..utils.smart_classifier import smart_classifier
from ..utils.interactive_menu import InteractiveDownloadMenu
from ..utils.media_extractor import MediaExtractor
from ..utils.download_service import DownloadService, ResourceMonitor
from ..config import DOWNLOAD_CONFIG, MAX_DIRECT_DOWNLOAD_SIZE, MEDIA_TYPES

# Configuration
logger = logging.getLogger('bot.download_cog')

class Download(commands.Cog):
    """Downloads media files from the channel with smart organization."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logger
        self.media_types = MEDIA_TYPES
        self.interactive_menu = InteractiveDownloadMenu(bot)

    @app_commands.command(name="download", description="Open interactive download menu with smart file organization")
    async def download_media(self, interaction: discord.Interaction):
        try:
            await self.interactive_menu.create_main_menu(interaction)
        except Exception as e:
            logger.error(f"Error in download_media: {e}")
            await interaction.response.send_message("❌ An error occurred while opening the download menu.", ephemeral=True)

    @app_commands.command(name="download_by_link", description="Download media from a specific message URL")
    @app_commands.describe(message_url="Discord message URL (right-click > Copy Link)")
    async def download_by_link(self, interaction: discord.Interaction, message_url: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            m = re.search(r"discord\.com/[^/]+/(\d+)/(\d+)/(\d+)", message_url)
            if not m:
                await interaction.followup.send("Invalid message URL.")
                return
            guild_id, channel_id, message_id = map(int, m.groups())

            channel = interaction.client.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await interaction.client.fetch_channel(channel_id)
                except Exception:
                    await interaction.followup.send("Cannot access the channel. Check bot permissions.")
                    return

            try:
                message = await channel.fetch_message(message_id)
            except Exception:
                await interaction.followup.send("Cannot fetch the message. The bot might not see this channel/thread.")
                return

            allowed_exts = self.media_types['all']
            media_list = MediaExtractor.extract(message, allowed_exts=allowed_exts)
            
            if not media_list:
                await interaction.followup.send("No media found in that message.")
                return

            temp_dir = DOWNLOAD_CONFIG['temp_dir']
            os.makedirs(temp_dir, exist_ok=True)
            downloaded_files = []
            total_size = 0
            
            for url, name in media_list:
                file_path = os.path.join(temp_dir, f"single_{len(downloaded_files)}_{name}")
                if await DownloadService.download_file_in_chunks(url, file_path):
                    downloaded_files.append(file_path)
                    total_size += os.path.getsize(file_path)

            if not downloaded_files:
                await interaction.followup.send("Failed to download media from the message.")
                return

            if len(downloaded_files) == 1 and total_size <= MAX_DIRECT_DOWNLOAD_SIZE:
                await interaction.followup.send(file=discord.File(downloaded_files[0]))
            else:
                zip_name = f"message_media_{message_id}.zip"
                zip_path = os.path.join(temp_dir, zip_name)
                
                await DownloadService.create_zip_in_chunks(downloaded_files, zip_path)
                
                if os.path.getsize(zip_path) <= MAX_DIRECT_DOWNLOAD_SIZE:
                    await interaction.followup.send(file=discord.File(zip_path))
                else:
                    uploader = CatboxUploader()
                    with open(zip_path, 'rb') as f:
                        data = f.read()
                    url = await uploader.upload_file(filename=zip_name, file_data=data)
                    await interaction.followup.send(f"File too large; uploaded to Catbox: {url}")

        except Exception as e:
            logger.error(f"Error in download_by_link: {e}")
            await interaction.followup.send(f"An error occurred: {e}")
            
        finally:
            # Clean temp files
            self._cleanup_temp_files(downloaded_files if 'downloaded_files' in locals() else [])
            if 'zip_path' in locals() and os.path.exists(zip_path):
                 try: os.remove(zip_path)
                 except: pass

    async def start_interactive_download(self, interaction: discord.Interaction, options: dict):
        try:
            media_type = options.get('media_type', 'all')
            message_limit = options.get('message_limit', 0)
            date_range = options.get('date_range', 'All time')
            
            monitor = ResourceMonitor()
            temp_dir = DOWNLOAD_CONFIG['temp_dir']
            os.makedirs(temp_dir, exist_ok=True)
            
            monitor.log_resources(logger)
            
            downloaded_files = []
            total_size = 0
            
            message_limit = None if message_limit <= 0 else message_limit
            
            progress_embed = self._create_initial_embed(media_type, date_range, message_limit)
            await interaction.response.edit_message(embed=progress_embed, view=None)
            
            try:
                channel_messages = []
                async for msg in interaction.channel.history(limit=message_limit):
                    channel_messages.append(msg)
                
                total_messages = len(channel_messages)
                self._update_progress_embed(progress_embed, f"✅ Found {total_messages} messages\n📥 Downloading media...")
                await interaction.edit_original_response(embed=progress_embed)

                failed_downloads = []
                monitor.start_monitoring(total_messages) # monitoring messages, not exactly items

                for msg in channel_messages:
                    allowed_exts = self.media_types[media_type]
                    # Key change: include_text_links=False
                    media_list = MediaExtractor.extract(msg, allowed_exts=allowed_exts, include_text_links=False)

                    for url, suggested_name in media_list:
                        # Trust MediaExtractor results. Do not re-filter extension.
                        # MediaExtractor handles "relaxed" mode and "trust discord" logic.
                        
                        file_path = os.path.join(temp_dir, f"{len(downloaded_files)}_{suggested_name}")

                        should_pause, reason = monitor.should_pause()
                        if should_pause:
                            self._update_progress_embed(progress_embed, f"⏸️ Paused: {reason}\nWaiting 30 seconds...")
                            await interaction.edit_original_response(embed=progress_embed)
                            await asyncio.sleep(30)

                        if await DownloadService.download_file_in_chunks(url, file_path):
                            downloaded_files.append(file_path)
                            total_size += os.path.getsize(file_path)
                        else:
                            failed_downloads.append(suggested_name)

                        # Update UI rarely
                        if len(downloaded_files) % 5 == 0:
                             await self._update_ui_progress(interaction, progress_embed, downloaded_files, total_messages, total_size, failed_downloads)
                
                if not downloaded_files:
                    await self._send_no_media_found(interaction, progress_embed, media_type)
                    return

                # Classification
                self._update_progress_embed(progress_embed, f"🧠 Smart organization of {len(downloaded_files)} files...")
                await interaction.edit_original_response(embed=progress_embed)
                
                organized_files = smart_classifier.organize_with_minimum_threshold(downloaded_files)
                stats = smart_classifier.get_organization_stats(organized_files)
                
                # Zipping
                self._update_progress_embed(progress_embed, "📦 Creating ZIP file...")
                await interaction.edit_original_response(embed=progress_embed)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_name = f"media_{media_type}_{timestamp}_organized.zip"
                zip_path = os.path.join(temp_dir, zip_name)
                
                # Use DownloadService for zipping
                # But we need flattened files list for stats? No, create_zip_in_chunks needs list of paths
                # But organzied_files is a dict.
                # Let's write a custom zip logic here or update DownloadService to handle dict.
                # Actually, DownloadService.create_zip_in_chunks takes `files: list`.
                # We need to flatten the dictionary but keep folder structure.
                # Wait, DownloadService is designed for flat list. 
                # I should just zip manually here to support the folder structure, OR update DownloadService to support structure.
                # For simplicity, I'll implement the zipping here properly supporting structure, using a helper.
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=DOWNLOAD_CONFIG['compress_level']) as zip_file:
                    for folder_key, file_list in organized_files.items():
                        for file_path in file_list:
                            if os.path.exists(file_path):
                                filename = os.path.basename(file_path)
                                zip_internal_path = f"{folder_key}/{filename}"
                                zip_file.write(file_path, zip_internal_path)
                                # Cleanup as we go
                                if DOWNLOAD_CONFIG['cleanup_after_zip']:
                                    try: os.remove(file_path)
                                    except: pass

                # Final Delivery
                file_size = os.path.getsize(zip_path)
                if file_size > MAX_DIRECT_DOWNLOAD_SIZE:
                    self._update_progress_embed(progress_embed, "☁️ Uploading to Catbox...", field_name="📊 Status")
                    await interaction.edit_original_response(embed=progress_embed)
                    
                    uploader = CatboxUploader()
                    with open(zip_path, 'rb') as f:
                        file_data = f.read()
                    url = await uploader.upload_file(filename=zip_name, file_data=file_data)
                    
                    progress_embed.title = "✅ Download Complete!"
                    progress_embed.color = 0x00FF00
                    self._update_progress_embed(progress_embed, f"**Files**: {len(downloaded_files)}\n**Size**: {file_size/1024/1024:.2f}MB\n[📥 Download Link]({url})", field_name="📊 Results")
                    await interaction.edit_original_response(embed=progress_embed)
                else:
                    progress_embed.title = "✅ Download Complete!"
                    progress_embed.color = 0x00FF00
                    self._update_progress_embed(progress_embed, f"**Files**: {len(downloaded_files)}\n**Size**: {file_size/1024/1024:.2f}MB\n⬇️ ZIP file below", field_name="📊 Results")
                    await interaction.edit_original_response(embed=progress_embed, attachments=[discord.File(zip_path)])

            finally:
                if 'zip_path' in locals() and os.path.exists(zip_path):
                    try: os.remove(zip_path)
                    except: pass
                # Redundant cleanup check
                self._cleanup_temp_files(downloaded_files)

        except Exception as e:
            logger.error(f"Error in start_interactive_download: {e}")
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

    def _cleanup_temp_files(self, files):
        for f in files:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass

    def _create_initial_embed(self, media_type, date_range, message_limit):
        embed = discord.Embed(
            title="📥 Download in Progress",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )
        embed.add_field(
            name="⚙️ Configuration",
            value=f"**Type**: {media_type.title()}\n**Period**: {date_range}\n**Limit**: {'All' if message_limit is None else message_limit}",
            inline=False
        )
        embed.add_field(name="📊 Status", value="Starting...", inline=False)
        return embed

    def _update_progress_embed(self, embed, value, field_name="📊 Status"):
        # Find field index
        index = -1
        for i, field in enumerate(embed.fields):
            if field.name == field_name:
                index = i
                break
        
        if index != -1:
            embed.set_field_at(index, name=field_name, value=value, inline=False)
        else:
            embed.add_field(name=field_name, value=value, inline=False)

    async def _update_ui_progress(self, interaction, embed, downloaded_files, total_total_est, total_size, failed):
        progress_text = f"Files: {len(downloaded_files)}\nSize: {total_size/1024/1024:.2f}MB"
        if failed:
            progress_text += f"\nFailed: {len(failed)}"
        self._update_progress_embed(embed, progress_text, field_name="📊 Progress")
        try:
             await interaction.edit_original_response(embed=embed)
        except:
             pass

    async def _send_no_media_found(self, interaction, embed, media_type):
        embed.title = "❌ No Media Found"
        embed.color = 0xFF0000
        self._update_progress_embed(embed, f"No {media_type} files found.", field_name="📊 Result")
        await interaction.edit_original_response(embed=embed)

    def _create_progress_bar(self, percent: float, length: int = 20) -> str:
        filled = int(length * percent / 100)
        bar = "█" * filled + "░" * (length - filled)
        return f"{bar} {percent:.1f}%"

async def setup(bot):
    await bot.add_cog(Download(bot))