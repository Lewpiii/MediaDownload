import discord
from discord.ext import commands
from discord import app_commands
import os
import aiohttp
import tempfile
import zipfile
import time
from datetime import datetime
from config import MEDIA_TYPES, MAX_DIRECT_DOWNLOAD_SIZE, CATEGORIES
from utils.gofile import GoFileUploader

class DownloadCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_vote(self, user_id: int) -> bool:
        """Vérifie si l'utilisateur a voté via l'API Top.gg"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": os.getenv('TOP_GG_TOKEN')}
                url = f"https://top.gg/api/bots/1332684877551763529/check?userId={user_id}"
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("voted") == 1
                    return False
        except Exception as e:
            print(f"Vote check error: {e}")
            return False

    async def check_permissions(self, channel: discord.TextChannel) -> bool:
        """Vérifie les permissions du bot dans le channel"""
        permissions = channel.permissions_for(channel.guild.me)
        required_permissions = {
            "read_messages": True,
            "send_messages": True,
            "attach_files": True,
            "read_message_history": True,
        }
        
        missing_permissions = [
            perm for perm, required in required_permissions.items()
            if getattr(permissions, perm) != required
        ]
        
        return not missing_permissions, missing_permissions

    @app_commands.command(name="download", description="Download media from this channel")
    @app_commands.choices(type=[
        app_commands.Choice(name="🖼️ Images", value="images"),
        app_commands.Choice(name="🎥 Videos", value="videos"),
        app_commands.Choice(name="📁 All", value="all")
    ])
    @app_commands.choices(number=[
        app_commands.Choice(name="Last 10 messages", value=10),
        app_commands.Choice(name="Last 20 messages", value=20),
        app_commands.Choice(name="Last 50 messages", value=50),
        app_commands.Choice(name="All messages", value=0)
    ])
    async def download_media(self, interaction: discord.Interaction, type: app_commands.Choice[str], number: app_commands.Choice[int]):
        # Debug: Afficher les paramètres reçus
        print(f"\n=== Download Command Debug ===")
        print(f"Type selected: {type.value}")
        print(f"Number selected: {number.value}")
        print(f"Channel: {interaction.channel.name} (ID: {interaction.channel.id})")
        print(f"Media types configured: {self.bot.media_types}")

        try:
            # Répondre immédiatement avec defer
            await interaction.response.defer(ephemeral=True)
            
            media_files = {'Images': [], 'Videos': []}
            total_size = 0
            messages_checked = 0
            files_found = 0
            
            await interaction.followup.send("🔍 Searching for media...", ephemeral=True)
            
            # Parcourir l'historique
            async for message in interaction.channel.history(limit=number.value):
                messages_checked += 1
                print(f"\nChecking message {messages_checked}")
                print(f"Message has {len(message.attachments)} attachments")
                
                for attachment in message.attachments:
                    ext = os.path.splitext(attachment.filename.lower())[1]
                    print(f"\nProcessing file: {attachment.filename}")
                    print(f"Extension: {ext}")
                    print(f"File size: {attachment.size} bytes")
                    
                    # Debug: Vérifier les conditions
                    if type.value == "images":
                        print(f"Checking if {ext} is in images: {ext in self.bot.media_types['images']}")
                    elif type.value == "videos":
                        print(f"Checking if {ext} is in videos: {ext in self.bot.media_types['videos']}")
                    else:  # all
                        print(f"Checking if {ext} is in all: {ext in self.bot.media_types['all']}")
                    
                    if type.value == "images" and ext in self.bot.media_types['images']:
                        print("✓ Adding as image")
                        media_files['Images'].append(attachment)
                        total_size += attachment.size
                        files_found += 1
                    elif type.value == "videos" and ext in self.bot.media_types['videos']:
                        print("✓ Adding as video")
                        media_files['Videos'].append(attachment)
                        total_size += attachment.size
                        files_found += 1
                    elif type.value == "all" and ext in self.bot.media_types['all']:
                        print("✓ Adding to all")
                        if ext in self.bot.media_types['images']:
                            media_files['Images'].append(attachment)
                        else:
                            media_files['Videos'].append(attachment)
                        total_size += attachment.size
                        files_found += 1
                    else:
                        print("✗ File not matching criteria")

            # Debug: Résumé
            print(f"\n=== Search Summary ===")
            print(f"Messages checked: {messages_checked}")
            print(f"Files found: {files_found}")
            print(f"Images: {len(media_files['Images'])}")
            print(f"Videos: {len(media_files['Videos'])}")
            print(f"Total size: {total_size} bytes")

            if not any(media_files.values()):
                await interaction.followup.send("❌ No media files found!", ephemeral=True)
                return

            # Si taille totale < 25MB, envoi direct en ZIP
            if total_size < MAX_DIRECT_DOWNLOAD_SIZE:
                await interaction.followup.send("📦 Preparing your files...", ephemeral=True)
                temp_zip = None
                try:
                    temp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
                    
                    with zipfile.ZipFile(temp_zip.name, 'w') as zf:
                        for media_type, files in media_files.items():
                            for file in files:
                                file_data = await file.read()
                                zf.writestr(f"{media_type}/{file.filename}", file_data)

                    await interaction.followup.send(
                        "📦 Here are your files:",
                        file=discord.File(temp_zip.name, 'media_files.zip')
                    )
                finally:
                    if temp_zip and os.path.exists(temp_zip.name):
                        os.unlink(temp_zip.name)
                return

            # Si > 25MB, vérifier le vote
            has_voted = await self.check_vote(interaction.user.id)
            if not has_voted:
                embed = discord.Embed(
                    title="⚠️ Vote Required",
                    description=(
                        "You need to vote for the bot to download large files!\n\n"
                        "📝 **Why vote?**\n"
                        "• Support the bot\n"
                        "• Get access to all features\n"
                        "• Help us grow\n\n"
                        "🔗 **Vote Link**\n"
                        "[Click here to vote](https://top.gg/bot/1332684877551763529/vote)\n\n"
                        "✨ **Free Features**\n"
                        "• Download files up to 25MB\n"
                        "• Direct ZIP downloads\n"
                    ),
                    color=0xFF0000
                )
                embed.set_footer(text="Your vote lasts 12 hours!")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Upload vers Gofile
            await interaction.followup.send("📤 Uploading files to Gofile...", ephemeral=True)
            
            uploader = GoFileUploader(os.getenv('GOFILE_TOKEN'))
            download_link = await uploader.organize_and_upload(media_files)

            embed = discord.Embed(
                title="✅ Download Ready!",
                description=(
                    f"📁 **Total Files:** {sum(len(files) for files in media_files.values())}\n"
                    f"📊 **Files:**\n"
                    f"• Images: {len(media_files['Images'])}\n"
                    f"• Videos: {len(media_files['Videos'])}\n\n"
                    f"🔗 **Download Link:**\n{download_link}"
                ),
                color=0x2ECC71
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Error in download_media: {e}")
            try:
                await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)
            except:
                print("Failed to send error message")

async def setup(bot):
    await bot.add_cog(DownloadCog(bot)) 