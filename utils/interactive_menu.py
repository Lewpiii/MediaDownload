"""
Interactive Menu System for Discord Bot
Provides user-friendly button-based navigation and options
"""
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncio
import logging

logger = logging.getLogger('bot.interactive')

class InteractiveDownloadMenu:
    """Interactive download menu with buttons and date selection"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_menus = {}  # Store active menu states
    
    async def create_main_menu(self, interaction: discord.Interaction):
        """Create the main download menu with options"""
        embed = discord.Embed(
            title="📥 Media Download Center",
            description="Choose your download options below:",
            color=0x00FF00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="🎯 Download Options",
            value=(
                "• **All Media**: Download everything from the channel\n"
                "• **By Date**: Download media from a specific date range\n"
                "• **By Type**: Download only images or videos\n"
                "• **Recent**: Download from last X messages"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🧠 Smart Features",
            value=(
                "• **Auto-Organization**: Files sorted by category\n"
                "• **Smart Folders**: Min 3 files per category\n"
                "• **Resource Monitoring**: Automatic pausing if needed"
            ),
            inline=False
        )
        
        embed.set_footer(text="Click a button below to start!")
        
        # Create buttons
        view = DownloadMenuView()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        # Store menu state
        self.active_menus[interaction.user.id] = {
            'channel': interaction.channel,
            'guild': interaction.guild,
            'step': 'main_menu'
        }
    
    async def create_date_selection_menu(self, interaction: discord.Interaction):
        """Create date selection menu"""
        embed = discord.Embed(
            title="📅 Select Date Range",
            description="Choose when to start downloading from:",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="📆 Quick Options",
            value=(
                "• **Last Hour**: Recent media only\n"
                "• **Today**: All media from today\n"
                "• **This Week**: Last 7 days\n"
                "• **This Month**: Last 30 days\n"
                "• **Custom**: Pick specific dates"
            ),
            inline=False
        )
        
        embed.set_footer(text="Select a time period or choose custom dates")
        
        view = DateSelectionView()
        
        await interaction.response.edit_message(embed=embed, view=view)
        
        # Update menu state
        if interaction.user.id in self.active_menus:
            self.active_menus[interaction.user.id]['step'] = 'date_selection'
    
    async def create_media_type_menu(self, interaction: discord.Interaction):
        """Create media type selection menu"""
        embed = discord.Embed(
            title="🎨 Select Media Type",
            description="Choose what type of media to download:",
            color=0xFF6B6B,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="📁 Media Types",
            value=(
                "• **🖼️ Images**: PNG, JPG, GIF, WebP\n"
                "• **🎥 Videos**: MP4, WebM, MOV\n"
                "• **📁 All Media**: Images + Videos\n"
                "• **🎵 Audio**: MP3, WAV, OGG (if any)"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 Expected Results",
            value=(
                "• **Images**: Usually smaller files\n"
                "• **Videos**: Larger files, may need external hosting\n"
                "• **All**: Complete media collection"
            ),
            inline=False
        )
        
        view = MediaTypeView()
        
        await interaction.response.edit_message(embed=embed, view=view)
        
        # Update menu state
        if interaction.user.id in self.active_menus:
            self.active_menus[interaction.user.id]['step'] = 'media_type_selection'
    
    async def create_confirmation_menu(self, interaction: discord.Interaction, options: Dict[str, Any]):
        """Create final confirmation menu"""
        embed = discord.Embed(
            title="✅ Confirm Download",
            description="Review your download settings:",
            color=0xFFD93D,
            timestamp=datetime.utcnow()
        )
        
        # Build options summary
        options_text = []
        if 'date_range' in options:
            options_text.append(f"**📅 Date Range**: {options['date_range']}")
        if 'media_type' in options:
            options_text.append(f"**🎨 Media Type**: {options['media_type']}")
        if 'message_limit' in options:
            options_text.append(f"**📊 Message Limit**: {options['message_limit']}")
        
        embed.add_field(
            name="⚙️ Download Settings",
            value="\n".join(options_text),
            inline=False
        )
        
        embed.add_field(
            name="🧠 Smart Organization",
            value=(
                "• Files will be automatically categorized\n"
                "• Folders created for categories with 3+ files\n"
                "• Remaining files go to 'Other' folder"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Important Notes",
            value=(
                "• Large downloads may take time\n"
                "• Files >25MB will be uploaded to external hosting\n"
                "• Download can be paused if system resources are low"
            ),
            inline=False
        )
        
        view = ConfirmationView(options)
        
        await interaction.response.edit_message(embed=embed, view=view)
        
        # Update menu state
        if interaction.user.id in self.active_menus:
            self.active_menus[interaction.user.id]['step'] = 'confirmation'
            self.active_menus[interaction.user.id]['options'] = options

class DownloadMenuView(discord.ui.View):
    """Main download menu buttons"""
    
    def __init__(self):
        super().__init__(timeout=300)  # 5 minutes timeout
    
    @discord.ui.button(label="📥 Download All", style=discord.ButtonStyle.primary, emoji="📥")
    async def download_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Download all media from channel"""
        options = {
            'media_type': 'all',
            'message_limit': 0,
            'date_range': 'All time'
        }
        
        menu = InteractiveDownloadMenu(interaction.client)
        await menu.create_confirmation_menu(interaction, options)
    
    @discord.ui.button(label="📅 By Date", style=discord.ButtonStyle.secondary, emoji="📅")
    async def by_date(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Select date range"""
        menu = InteractiveDownloadMenu(interaction.client)
        await menu.create_date_selection_menu(interaction)
    
    @discord.ui.button(label="🎨 By Type", style=discord.ButtonStyle.secondary, emoji="🎨")
    async def by_type(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Select media type"""
        menu = InteractiveDownloadMenu(interaction.client)
        await menu.create_media_type_menu(interaction)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel download"""
        embed = discord.Embed(
            title="❌ Download Cancelled",
            description="No files were downloaded.",
            color=0xFF0000
        )
        await interaction.response.edit_message(embed=embed, view=None)

class DateSelectionView(discord.ui.View):
    """Date selection buttons"""
    
    def __init__(self):
        super().__init__(timeout=300)
    
    @discord.ui.button(label="⏰ Last Hour", style=discord.ButtonStyle.primary)
    async def last_hour(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Download from last hour"""
        options = {
            'media_type': 'all',
            'message_limit': 50,  # Approximate for 1 hour
            'date_range': 'Last hour'
        }
        
        menu = InteractiveDownloadMenu(interaction.client)
        await menu.create_confirmation_menu(interaction, options)
    
    @discord.ui.button(label="📅 Today", style=discord.ButtonStyle.secondary)
    async def today(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Download from today"""
        options = {
            'media_type': 'all',
            'message_limit': 200,  # Approximate for 1 day
            'date_range': 'Today'
        }
        
        menu = InteractiveDownloadMenu(interaction.client)
        await menu.create_confirmation_menu(interaction, options)
    
    @discord.ui.button(label="📆 This Week", style=discord.ButtonStyle.secondary)
    async def this_week(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Download from this week"""
        options = {
            'media_type': 'all',
            'message_limit': 1000,  # Approximate for 1 week
            'date_range': 'This week'
        }
        
        menu = InteractiveDownloadMenu(interaction.client)
        await menu.create_confirmation_menu(interaction, options)
    
    @discord.ui.button(label="📊 This Month", style=discord.ButtonStyle.secondary)
    async def this_month(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Download from this month"""
        options = {
            'media_type': 'all',
            'message_limit': 5000,  # Approximate for 1 month
            'date_range': 'This month'
        }
        
        menu = InteractiveDownloadMenu(interaction.client)
        await menu.create_confirmation_menu(interaction, options)
    
    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go back to main menu"""
        embed = discord.Embed(
            title="📥 Media Download Center",
            description="Choose your download options below:",
            color=0x00FF00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="🎯 Download Options",
            value=(
                "• **All Media**: Download everything from the channel\n"
                "• **By Date**: Download media from a specific date range\n"
                "• **By Type**: Download only images or videos\n"
                "• **Recent**: Download from last X messages"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🧠 Smart Features",
            value=(
                "• **Auto-Organization**: Files sorted by category\n"
                "• **Smart Folders**: Min 3 files per category\n"
                "• **Resource Monitoring**: Automatic pausing if needed"
            ),
            inline=False
        )
        
        embed.set_footer(text="Click a button below to start!")
        
        view = DownloadMenuView()
        await interaction.response.edit_message(embed=embed, view=view)

class MediaTypeView(discord.ui.View):
    """Media type selection buttons"""
    
    def __init__(self):
        super().__init__(timeout=300)
    
    @discord.ui.button(label="🖼️ Images Only", style=discord.ButtonStyle.primary)
    async def images_only(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Download images only"""
        options = {
            'media_type': 'images',
            'message_limit': 0,
            'date_range': 'All time'
        }
        
        menu = InteractiveDownloadMenu(interaction.client)
        await menu.create_confirmation_menu(interaction, options)
    
    @discord.ui.button(label="🎥 Videos Only", style=discord.ButtonStyle.secondary)
    async def videos_only(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Download videos only"""
        options = {
            'media_type': 'videos',
            'message_limit': 0,
            'date_range': 'All time'
        }
        
        menu = InteractiveDownloadMenu(interaction.client)
        await menu.create_confirmation_menu(interaction, options)
    
    @discord.ui.button(label="📁 All Media", style=discord.ButtonStyle.secondary)
    async def all_media(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Download all media"""
        options = {
            'media_type': 'all',
            'message_limit': 0,
            'date_range': 'All time'
        }
        
        menu = InteractiveDownloadMenu(interaction.client)
        await menu.create_confirmation_menu(interaction, options)
    
    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go back to main menu"""
        embed = discord.Embed(
            title="📥 Media Download Center",
            description="Choose your download options below:",
            color=0x00FF00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="🎯 Download Options",
            value=(
                "• **All Media**: Download everything from the channel\n"
                "• **By Date**: Download media from a specific date range\n"
                "• **By Type**: Download only images or videos\n"
                "• **Recent**: Download from last X messages"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🧠 Smart Features",
            value=(
                "• **Auto-Organization**: Files sorted by category\n"
                "• **Smart Folders**: Min 3 files per category\n"
                "• **Resource Monitoring**: Automatic pausing if needed"
            ),
            inline=False
        )
        
        embed.set_footer(text="Click a button below to start!")
        
        view = DownloadMenuView()
        await interaction.response.edit_message(embed=embed, view=view)

class ConfirmationView(discord.ui.View):
    """Final confirmation buttons"""
    
    def __init__(self, options: Dict[str, Any]):
        super().__init__(timeout=300)
        self.options = options
    
    @discord.ui.button(label="✅ Start Download", style=discord.ButtonStyle.success)
    async def start_download(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start the download process"""
        # Import here to avoid circular imports
        from cogs.download import Download
        
        # Get the download cog
        download_cog = interaction.client.get_cog('Download')
        if download_cog:
            # Start download with the selected options
            await download_cog.start_interactive_download(interaction, self.options)
        else:
            await interaction.response.send_message(
                "❌ Download system not available. Please try again later.",
                ephemeral=True
            )
    
    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go back to main menu"""
        embed = discord.Embed(
            title="📥 Media Download Center",
            description="Choose your download options below:",
            color=0x00FF00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="🎯 Download Options",
            value=(
                "• **All Media**: Download everything from the channel\n"
                "• **By Date**: Download media from a specific date range\n"
                "• **By Type**: Download only images or videos\n"
                "• **Recent**: Download from last X messages"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🧠 Smart Features",
            value=(
                "• **Auto-Organization**: Files sorted by category\n"
                "• **Smart Folders**: Min 3 files per category\n"
                "• **Resource Monitoring**: Automatic pausing if needed"
            ),
            inline=False
        )
        
        embed.set_footer(text="Click a button below to start!")
        
        view = DownloadMenuView()
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel download"""
        embed = discord.Embed(
            title="❌ Download Cancelled",
            description="No files were downloaded.",
            color=0xFF0000
        )
        await interaction.response.edit_message(embed=embed, view=None)
