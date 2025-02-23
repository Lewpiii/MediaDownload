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
        try:
            # 1. Répondre immédiatement
            await interaction.response.defer()
            
            # 2. Initialisation
            media_files = {'Images': [], 'Videos': []}
            total_size = 0
            
            # 3. Premier message de status
            status_message = await interaction.followup.send("🔍 Searching for media...", wait=True)
            
            # 4. Parcourir les messages
            async for message in interaction.channel.history(limit=number.value or None):
                for attachment in message.attachments:
                    ext = os.path.splitext(attachment.filename.lower())[1]
                    
                    if type.value == "images" and ext in self.bot.media_types['images']:
                        media_files['Images'].append(attachment)
                        total_size += attachment.size
                    elif type.value == "videos" and ext in self.bot.media_types['videos']:
                        media_files['Videos'].append(attachment)
                        total_size += attachment.size
                    elif type.value == "all" and ext in self.bot.media_types['all']:
                        if ext in self.bot.media_types['images']:
                            media_files['Images'].append(attachment)
                        else:
                            media_files['Videos'].append(attachment)
                        total_size += attachment.size

            # 5. Vérifier si des fichiers ont été trouvés
            if not any(media_files.values()):
                await status_message.edit(content="❌ No media files found!")
                return

            # 6. Envoi direct si < 25MB
            if total_size < MAX_DIRECT_DOWNLOAD_SIZE:
                await status_message.edit(content="📦 Preparing your files...")
                
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
                    with zipfile.ZipFile(temp_zip.name, 'w') as zf:
                        for media_type, files in media_files.items():
                            for file in files:
                                file_data = await file.read()
                                zf.writestr(f"{media_type}/{file.filename}", file_data)
                    
                    await interaction.followup.send(
                        "📦 Here are your files:",
                        file=discord.File(temp_zip.name, 'media_files.zip')
                    )
                    
                    # Nettoyage
                    os.unlink(temp_zip.name)
                return

            # 7. Sinon, vérifier le vote
            has_voted = await self.check_vote(interaction.user.id)
            if not has_voted:
                embed = discord.Embed(
                    title="⚠️ Vote Required",
                    description="You need to vote for the bot to download large files!",
                    color=0xFF0000
                )
                await status_message.edit(embed=embed)
                return

            # 8. Upload Gofile
            await status_message.edit(content="📤 Uploading files to Gofile...")
            uploader = GoFileUploader(os.getenv('GOFILE_TOKEN'))
            download_link = await uploader.organize_and_upload(media_files)

            embed = discord.Embed(
                title="✅ Download Ready!",
                description=f"🔗 **Download Link:**\n{download_link}",
                color=0x2ECC71
            )
            await status_message.edit(embed=embed)

        except Exception as e:
            print(f"Error in download_media: {e}")
            try:
                await interaction.followup.send(f"❌ An error occurred: {str(e)}")
            except:
                print("Failed to send error message")

async def setup(bot):
    await bot.add_cog(DownloadCog(bot)) 