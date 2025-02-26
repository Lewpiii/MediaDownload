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
import aiofiles
import shutil
import typing

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
        self.bot.media_types = {
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
            'videos': ['.mp4', '.webm', '.mov', '.avi'],
            'all': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.webm', '.mov', '.avi']
        }
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
    @app_commands.choices(messages=[  # 0 signifiera "all"
        app_commands.Choice(name="Last 100", value=100),
        app_commands.Choice(name="Last 1000", value=1000),
        app_commands.Choice(name="All messages", value=0)
    ])
    async def download_media(self, interaction: discord.Interaction, type: str, messages: int = 100):
        try:
            await interaction.response.defer()
            
            # Récupérer les messages
            limit = None if messages == 0 else messages
            attachments = []
            
            async for message in interaction.channel.history(limit=limit):
                attachments.extend(message.attachments)

            if not attachments:
                await interaction.followup.send("❌ No attachments found!")
                return

            await self.process_attachments(interaction, attachments, type)

        except Exception as e:
            print(f"Error in download_media: {e}")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

    async def process_attachments(self, interaction, attachments, type):
        """Traite les attachments avec streaming sur SSD"""
        try:
            total_files = len(attachments)
            processed = 0
            
            # Utiliser un dossier temporaire sur le SSD
            temp_dir = '/home/botuser/discord-bot/temp'
            os.makedirs(temp_dir, exist_ok=True)
            
            # Créer un sous-dossier unique pour cette opération
            session_dir = os.path.join(temp_dir, f'download_{int(time.time())}')
            os.makedirs(os.path.join(session_dir, "Images"), exist_ok=True)
            os.makedirs(os.path.join(session_dir, "Videos"), exist_ok=True)

            try:
                status_message = await interaction.followup.send(
                    f"⏳ Processing 0/{total_files} files...",
                    wait=True
                )

                # Traiter chaque fichier
                for attachment in attachments:
                    ext = os.path.splitext(attachment.filename.lower())[1]
                    if ((type == "images" and ext in self.bot.media_types['images']) or
                        (type == "videos" and ext in self.bot.media_types['videos']) or
                        (type == "all" and ext in self.bot.media_types['all'])):
                        
                        # Déterminer le dossier de destination
                        folder = "Images" if ext in self.bot.media_types['images'] else "Videos"
                        file_path = os.path.join(session_dir, folder, attachment.filename)
                        
                        # Stream le fichier sur le SSD
                        async with aiohttp.ClientSession() as session:
                            async with session.get(attachment.url) as response:
                                if response.status == 200:
                                    async with aiofiles.open(file_path, 'wb') as f:
                                        async for data in response.content.iter_chunked(8192):
                                            await f.write(data)
                        
                        processed += 1
                        if processed % 5 == 0:  # Update tous les 5 fichiers
                            await status_message.edit(
                                content=f"⏳ Processing {processed}/{total_files} files..."
                            )

                # Créer le ZIP en streaming
                zip_path = os.path.join(temp_dir, f'media_files_{int(time.time())}.zip')
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for folder in ["Images", "Videos"]:
                        folder_path = os.path.join(session_dir, folder)
                        if os.path.exists(folder_path):
                            for root, _, files in os.walk(folder_path):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    arc_name = os.path.relpath(file_path, session_dir)
                                    zipf.write(file_path, arc_name)

                # Upload le ZIP
                await status_message.edit(content="⏳ Uploading to file host...")
                async with aiofiles.open(zip_path, 'rb') as f:
                    file_data = await f.read()
                    await interaction.followup.send(file=discord.File(
                        fp=zip_path,
                        filename="media_files.zip"
                    ))

            finally:
                # Nettoyer les fichiers temporaires
                if os.path.exists(session_dir):
                    shutil.rmtree(session_dir)
                if os.path.exists(zip_path):
                    os.remove(zip_path)

        except Exception as e:
            print(f"Error in process_attachments: {e}")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

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
    async def download(self, ctx, channel: typing.Optional[discord.TextChannel] = None, limit: typing.Optional[int] = None):
        """Télécharge et organise les médias du message ou du channel
        
        Usage:
        !dl - Télécharge les médias du message actuel ou référencé
        !dl #channel - Télécharge tous les médias du channel spécifié
        !dl #channel 10 - Télécharge les médias des 10 derniers messages du channel
        """
        try:
            attachments = []

            # Si un channel est spécifié
            if channel:
                loading_msg = await ctx.send(f"⏳ Recherche des médias dans {channel.mention}...")
                
                # Récupérer les messages
                if limit:
                    messages = [msg async for msg in channel.history(limit=limit)]
                else:
                    messages = [msg async for msg in channel.history(limit=None)]  # Pas de limite
                
                # Collecter tous les attachments
                for msg in messages:
                    attachments.extend(msg.attachments)
                
                await loading_msg.edit(content=f"📂 Trouvé {len(attachments)} fichiers...")

            # Sinon, vérifier le message actuel ou référencé
            else:
                if not ctx.message.attachments:
                    if ctx.message.reference:  # Message référencé
                        referenced_msg = await ctx.fetch_message(ctx.message.reference.message_id)
                        attachments = referenced_msg.attachments
                    else:
                        await ctx.send("❌ Aucun média trouvé. Utilisez `!dl #channel` pour télécharger depuis un channel.")
                        return
                else:
                    attachments = ctx.message.attachments

            if not attachments:
                await ctx.send("❌ Aucun média trouvé dans les messages.")
                return

            # Message de chargement avec progression
            if not channel:  # Si on n'a pas déjà créé le message de chargement
                loading_msg = await ctx.send("⏳ Analyse des fichiers en cours...")

            # Organiser les fichiers par type
            media_files: Dict[str, List[discord.Attachment]] = {}
            for attachment in attachments:
                file_type = attachment.filename.split('.')[-1].lower()
                if file_type not in media_files:
                    media_files[file_type] = []
                media_files[file_type].append(attachment)

            # Mettre à jour le message de chargement
            await loading_msg.edit(content=f"⚙️ Traitement de {len(attachments)} fichiers...")

            # Upload les fichiers
            stats, url = await self.uploader.organize_and_upload(media_files)

            # Formater et envoyer le message final
            response = self.format_stats(stats)
            response += f"\n\n🔗 Download Link:\n{url}"

            await loading_msg.edit(content=response)

        except Exception as e:
            await ctx.send(f"❌ Une erreur est survenue: {str(e)}")
            print(f"Error in download command: {e}")

    async def upload_file(self, filename: str, content: bytes):
        """Upload a file to the configured service"""
        try:
            # Ensure filename is str
            if isinstance(filename, bytes):
                filename = filename.decode('utf-8')
            
            # Ensure content is bytes
            if not isinstance(content, bytes):
                content = bytes(content)
                
            return await self.uploader.upload_file(filename, content)
        except Exception as e:
            print(f"Error uploading file: {str(e)}")
            raise

    async def send_large_file(self, interaction, file_path):
        """Send a large file in chunks using streaming."""
        CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB chunks
        MAX_RETRIES = 3
        
        try:
            file_size = os.path.getsize(file_path)
            
            # Si le fichier est petit, l'envoyer directement
            if file_size <= CHUNK_SIZE:
                await interaction.followup.send(file=discord.File(file_path))
                return

            # Pour les gros fichiers, utiliser le streaming
            async with aiofiles.open(file_path, 'rb') as f:
                chunk_number = 1
                total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
                
                while True:
                    chunk = await f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                        
                    # Créer un fichier temporaire pour le chunk
                    temp_path = f"{file_path}.part{chunk_number}"
                    try:
                        async with aiofiles.open(temp_path, 'wb') as temp_file:
                            await temp_file.write(chunk)
                        
                        # Envoyer avec retry en cas d'erreur
                        for attempt in range(MAX_RETRIES):
                            try:
                                await interaction.followup.send(
                                    content=f"Sending part {chunk_number}/{total_chunks}...",
                                    file=discord.File(temp_path)
                                )
                                break
                            except Exception as e:
                                if attempt == MAX_RETRIES - 1:
                                    raise
                                await asyncio.sleep(1)
                                
                    finally:
                        # Nettoyer le fichier temporaire
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                    
                    chunk_number += 1
                    
                    # Libérer la mémoire explicitement
                    del chunk
                    await asyncio.sleep(0.5)  # Petit délai entre les chunks
                    
        except Exception as e:
            print(f"Error in send_large_file: {e}")
            raise
        finally:
            # S'assurer que tous les fichiers temporaires sont nettoyés
            for i in range(1, chunk_number):
                temp_path = f"{file_path}.part{i}"
                if os.path.exists(temp_path):
                    os.remove(temp_path)

async def setup(bot):
    await bot.add_cog(DownloadCog(bot)) 