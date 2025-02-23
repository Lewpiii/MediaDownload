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
from utils.catbox import CatboxUploader
from typing import Dict, List
import asyncio

def format_size(size_bytes: int) -> str:
    """Convertit les bytes en format lisible"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

class DownloadCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.uploader = CatboxUploader()

    async def check_vote(self, user_id: int) -> bool:
        """Vérifie si l'utilisateur a voté via l'API Top.gg"""
        token = os.getenv('TOP_GG_TOKEN')
        if not token:
            print("⚠️ TOP_GG_TOKEN not found in environment variables")
            return True  # En cas de problème avec le token, on laisse passer
            
        try:
            print(f"\n=== Vote Check Debug ===")
            print(f"Checking vote for user ID: {user_id}")
            
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": token}
                url = f"https://top.gg/api/bots/1332684877551763529/check?userId={user_id}"
                
                print(f"Making request to: {url}")
                async with session.get(url, headers=headers) as response:
                    print(f"Response status: {response.status}")
                    response_text = await response.text()
                    print(f"Raw response: {response_text}")
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            print(f"Parsed response data: {data}")
                            has_voted = bool(data.get("voted", 0))
                            print(f"Has voted: {has_voted}")
                            return has_voted
                        except Exception as e:
                            print(f"Error parsing response: {e}")
                            return True  # En cas d'erreur de parsing, on laisse passer
                    else:
                        print(f"Unexpected status code: {response.status}")
                        return True  # En cas d'erreur d'API, on laisse passer
                        
        except Exception as e:
            print(f"Error during vote check: {e}")
            return True  # En cas d'erreur, on laisse passer

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
            
            # 2. Premier message de status
            status_message = await interaction.followup.send("🔍 Searching for media...", wait=True)
            
            # 3. Initialisation
            media_files = {'Images': [], 'Videos': []}
            total_size = 0
            
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
                vote_embed = discord.Embed(
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
                        "• Direct ZIP downloads\n\n"
                        "🎁 **Premium Features** (after voting)\n"
                        "• Download files of any size\n"
                        "• Organize files by category\n"
                        "• Permanent download links"
                    ),
                    color=0xFF0000
                )
                vote_embed.set_footer(text="Your vote lasts 12 hours!")
                await status_message.edit(content=None, embed=vote_embed)
                return

            # 8. Upload Gofile
            await status_message.edit(content="📤 Uploading files...")
            stats, download_link = await self.uploader.organize_and_upload(media_files)

            success_embed = discord.Embed(
                title="✅ Download Ready!",
                description=(
                    f"📁 Total: {stats['total']} files ({format_size(stats['total_size'])})\n"
                    f"📊 By Type:\n"
                    f"• Images: {stats['types']['Images']['count']} files ({format_size(stats['types']['Images']['size'])})\n"
                    f"• Videos: {stats['types']['Videos']['count']} files ({format_size(stats['types']['Videos']['size'])})\n\n"
                    f"🎁 **Stats:**\n"
                    f"• Total: {stats['total']}\n"
                    f"• Types: {', '.join(f'{media_type}: {count}' for media_type, count in stats['types'].items())}\n\n"
                    f"📑 Details:\n"
                    f"• Images: {stats['types']['Images']['count']} files ({format_size(stats['types']['Images']['size'])})\n"
                    f"• Videos: {stats['types']['Videos']['count']} files ({format_size(stats['types']['Videos']['size'])})\n"
                ),
                color=0x2ECC71
            )
            success_embed.add_field(name="🔗 Download Link:", value=download_link)
            await status_message.edit(content=None, embed=success_embed)

        except Exception as e:
            print(f"Error in download_media: {e}")
            try:
                await status_message.edit(content=f"❌ An error occurred: {str(e)}")
            except:
                print("Failed to send error message")

    @app_commands.command(name="checkvote", description="Check your vote status")
    async def check_vote_status(self, interaction: discord.Interaction):
        """Commande de debug pour vérifier le statut de vote"""
        await interaction.response.defer(ephemeral=True)
        
        has_voted = await self.check_vote(interaction.user.id)
        
        embed = discord.Embed(
            title="Vote Status Check",
            description=(
                f"User ID: {interaction.user.id}\n"
                f"Has voted: {has_voted}\n"
                f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            ),
            color=0x00FF00 if has_voted else 0xFF0000
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    def format_stats(self, stats: Dict) -> str:
        """Formate les statistiques en message lisible"""
        total_size = format_size(stats['total_size'])
        response = [
            "✅ Download Ready!",
            f"📁 Total: {stats['total']} files ({total_size})\n"
        ]

        # Statistiques par type principal
        response.append("📊 By Type:")
        for media_type, type_stats in stats['types'].items():
            if type_stats['count'] > 0:
                type_size = format_size(type_stats['size'])
                response.append(f"• {media_type}: {type_stats['count']} files ({type_size})")

        # Détails par catégorie
        response.append("\n📑 Details:")
        for category, cat_stats in stats['categories'].items():
            if category != "Others" and cat_stats['count'] > 0:
                cat_size = format_size(cat_stats['size'])
                response.append(f"• {category}: {cat_stats['count']} files ({cat_size})")
                
                # Sous-catégories
                for subcat, subcat_stats in cat_stats['subcategories'].items():
                    if subcat_stats['count'] > 0:
                        subcat_size = format_size(subcat_stats['size'])
                        response.append(f"  - {subcat}: {subcat_stats['count']} ({subcat_size})")

        # Fichiers non classés
        if "Others" in stats['categories'] and stats['categories']['Others']['count'] > 0:
            others_size = format_size(stats['categories']['Others']['size'])
            response.append(f"\n📦 Unclassified: {stats['categories']['Others']['count']} files ({others_size})")

        return "\n".join(response)

    @commands.command(name='dl')
    async def download(self, ctx):
        """Télécharge et organise les médias du message"""
        try:
            # Vérifier s'il y a des pièces jointes
            if not ctx.message.attachments:
                if ctx.message.reference:  # Vérifier s'il y a un message référencé
                    referenced_msg = await ctx.fetch_message(ctx.message.reference.message_id)
                    attachments = referenced_msg.attachments
                else:
                    await ctx.send("❌ Aucun média trouvé")
                    return
            else:
                attachments = ctx.message.attachments

            if not attachments:
                await ctx.send("❌ Aucun média trouvé")
                return

            # Message de chargement avec progression
            loading_msg = await ctx.send("⏳ Analyse des fichiers en cours...")

            # Organiser les fichiers par type
            media_files: Dict[str, List[discord.Attachment]] = {}
            for attachment in attachments:
                file_type = attachment.filename.split('.')[-1].lower()
                if file_type not in media_files:
                    media_files[file_type] = []
                media_files[file_type].append(attachment)

            # Mettre à jour le message de chargement
            await loading_msg.edit(content="⏳ Classification et organisation des fichiers...")

            # Upload les fichiers
            stats, url = await self.uploader.organize_and_upload(media_files)

            # Formater et envoyer le message final
            response = self.format_stats(stats)
            response += f"\n\n🔗 Download Link:\n{url}"

            await loading_msg.edit(content=response)

        except Exception as e:
            await ctx.send(f"❌ Une erreur est survenue: {str(e)}")
            print(f"Error in download command: {e}")

async def setup(bot):
    await bot.add_cog(DownloadCog(bot)) 