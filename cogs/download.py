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
from utils.logging import Logger
import logging

# Configuration du logger avec plus de détails
logger = logging.getLogger('bot.download')
logger.setLevel(logging.DEBUG)  # Augmente le niveau de détail

# Configuration
MAX_DISCORD_SIZE = 25 * 1024 * 1024  # 25MB limite Discord

async def setup(bot):
    logger.info("Setting up Download cog")  # Log de setup
    try:
        await bot.add_cog(Download(bot))
        logger.info("Download cog successfully added")
    except Exception as e:
        logger.error(f"Error setting up Download cog: {e}")
        raise

class Download(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logger
        self.media_types = {
            'images': ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
            'videos': ['.mp4', '.webm', '.mov'],
            'all': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.webm', '.mov']
        }
        # Initialisation sécurisée de top.gg
        self.has_topgg = False
        try:
            import topgg
            if token := os.getenv('TOP_GG_TOKEN'):
                self.topgg = topgg.DBLClient(bot, token)
                self.has_topgg = True
                logger.info("Top.gg integration enabled")
            else:
                logger.warning("TOP_GG_TOKEN not found")
        except ImportError:
            logger.warning("topgg module not installed")

        # Initialisation sécurisée du channel ID
        try:
            channel_id = os.getenv('LOGS_CHANNEL_ID')
            self.logs_channel_id = int(channel_id) if channel_id else None
            logger.debug(f"Logs channel ID set to: {self.logs_channel_id}")  # Log du channel ID
        except (ValueError, TypeError):
            self.logger.warning("Invalid LOGS_CHANNEL_ID, logging will be disabled")
            self.logs_channel_id = None

    async def cog_load(self):
        """Appelé quand le cog est chargé"""
        logger.info("Download cog is loading")  # Log de chargement
        try:
            # Synchroniser les commandes du cog
            logger.info("Attempting to sync commands for Download cog")
            if not hasattr(self.bot, 'tree'):
                logger.error("Bot doesn't have a command tree!")
                return
            
            # Vérifier si la commande est dans l'arbre
            commands = await self.bot.tree.fetch_commands()
            logger.info(f"Current commands: {[cmd.name for cmd in commands]}")
        except Exception as e:
            logger.error(f"Error in cog_load: {e}")

    async def download_attachment(self, url: str, temp_dir: str) -> str:
        """Télécharge un fichier depuis une URL"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    file_name = url.split('/')[-1]
                    file_path = os.path.join(temp_dir, file_name)
                    with open(file_path, 'wb') as f:
                        f.write(await response.read())
                    return file_path
                return None

    async def check_vote(self, user_id: int) -> bool:
        """Vérifie si l'utilisateur a voté pour le bot"""
        if not self.has_topgg:
            return True  # Si top.gg n'est pas configuré, on autorise
        try:
            return await self.topgg.get_user_vote(user_id)
        except Exception as e:
            logger.error(f"Error checking vote: {e}")
            return True  # En cas d'erreur, on autorise

    @app_commands.command(
        name="download",
        description="Download media from this channel"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="🖼️ Images", value="images"),
        app_commands.Choice(name="🎥 Videos", value="videos"),
        app_commands.Choice(name="📁 All", value="all")
    ])
    @app_commands.describe(
        type="Type de médias à télécharger",
        messages="Nombre de messages à analyser (0 = tous les messages)"
    )
    async def download_media(self, interaction: discord.Interaction, type: str, messages: int = 0):
        try:
            await interaction.response.defer(thinking=True)  # Ajout de thinking=True pour les longues opérations
            logger.debug(f"Starting download with type: {type}, messages: {messages}")

            # Créer un dossier temporaire
            with tempfile.TemporaryDirectory() as temp_dir:
                downloaded_files = []
                
                # Si messages = 0, on ne met pas de limite (None)
                message_limit = None if messages <= 0 else messages
                logger.debug(f"Fetching messages from channel {interaction.channel.name} with limit: {message_limit}")
                
                # Message d'information pour l'utilisateur si on cherche tous les messages
                if message_limit is None:
                    await interaction.followup.send("🔍 Recherche dans tous les messages du canal... Cela peut prendre un moment.")
                
                try:
                    channel_messages = []
                    async for msg in interaction.channel.history(limit=message_limit):
                        channel_messages.append(msg)
                    logger.debug(f"Successfully fetched {len(channel_messages)} messages")
                    
                    # Message de progression
                    await interaction.followup.send(f"📥 {len(channel_messages)} messages analysés, traitement des fichiers en cours...")
                except Exception as e:
                    logger.error(f"Error fetching messages: {e}")
                    await interaction.followup.send("❌ Erreur lors de la récupération des messages.")
                    return
                
                # Télécharger les fichiers
                for message in channel_messages:
                    for attachment in message.attachments:
                        file_ext = os.path.splitext(attachment.filename)[1].lower()
                        if file_ext in self.media_types[type]:
                            logger.debug(f"Found matching file: {attachment.filename}")
                            async with aiohttp.ClientSession() as session:
                                async with session.get(attachment.url) as response:
                                    if response.status == 200:
                                        file_path = os.path.join(temp_dir, attachment.filename)
                                        with open(file_path, 'wb') as f:
                                            f.write(await response.read())
                                        downloaded_files.append(file_path)

                if not downloaded_files:
                    msg = "❌ Aucun média trouvé"
                    if messages > 0:
                        msg += f" dans les {messages} derniers messages"
                    else:
                        msg += " dans le canal"
                    msg += f" de type {type}"
                    await interaction.followup.send(msg)
                    return

                # Créer le zip
                zip_path = os.path.join(temp_dir, f"media_{type}.zip")
                with zipfile.ZipFile(zip_path, 'w') as zip_file:
                    for file in downloaded_files:
                        zip_file.write(file, os.path.basename(file))

                # Vérifier la taille du zip
                file_size = os.path.getsize(zip_path)
                logger.debug(f"Zip size: {file_size / (1024*1024):.2f}MB")

                if file_size > MAX_DISCORD_SIZE:
                    # Vérifier si l'utilisateur a voté
                    has_voted = await self.check_vote(interaction.user.id)
                    if not has_voted:
                        vote_url = f"https://top.gg/bot/{self.bot.user.id}/vote"
                        embed = discord.Embed(
                            title="⭐ Vote requis !",
                            description=(
                                f"Le fichier fait {file_size / (1024*1024):.2f}MB et dépasse la limite Discord de 25MB.\n"
                                f"Pour télécharger des fichiers plus volumineux, votez pour le bot sur top.gg !\n"
                                f"[Cliquez ici pour voter]({vote_url})"
                            ),
                            color=discord.Color.gold()
                        )
                        await interaction.followup.send(embed=embed)
                        return

                    # Si l'utilisateur a voté, utiliser Catbox
                    logger.debug("User has voted, using Catbox")
                    uploader = CatboxUploader()
                    url = await uploader.upload(zip_path)
                    await interaction.followup.send(
                        f"📦 Fichier volumineux ({file_size / (1024*1024):.2f}MB).\n"
                        f"Téléchargez-le ici : {url}"
                    )
                else:
                    # Envoyer directement via Discord
                    logger.debug("Sending file via Discord")
                    await interaction.followup.send(
                        f"📦 {len(downloaded_files)} fichiers trouvés",
                        file=discord.File(zip_path)
                    )

        except Exception as e:
            logger.error(f"Error in download_media: {e}")
            await interaction.followup.send("❌ Une erreur est survenue lors du téléchargement.")

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

def format_size(size_bytes: int) -> str:
    """Convertit les bytes en format lisible"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB" 