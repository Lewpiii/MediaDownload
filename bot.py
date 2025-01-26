import discord
from discord import app_commands
from discord.ext import commands
import os
import io
import re
from datetime import datetime
from dotenv import load_dotenv

# Configuration
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if TOKEN is None:
    raise ValueError("❌ Token Discord non trouvé dans le fichier .env")

class MediaDownload(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='/', intents=intents)
        
        # Types de médias supportés
        self.media_types = {
            '📷 images': ['.jpg', '.jpeg', '.png', '.webp'],
            '🎥 videos': ['.mp4', '.mov', '.webm'],
            '🎞️ gifs': ['.gif'],
            '📁 all': []
        }
        self.media_types['📁 all'] = [ext for types in self.media_types.values() for ext in types]

    async def setup_hook(self):
        await self.add_cog(DownloadCog(self))
        print("🔄 Synchronisation des commandes slash...")
        try:
            synced = await self.tree.sync()
            print(f"✅ {len(synced)} commandes slash synchronisées !")
        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation : {e}")

class DownloadCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = 0x2ecc71  # Vert

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ {self.bot.user} est prêt !")
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="/help pour l'aide"
            )
        )

    @app_commands.command(name="help", description="Affiche l'aide du bot")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📥 Aide MediaDownload",
            description="Téléchargez facilement les médias d'un canal",
            color=self.color
        )
        
        embed.add_field(
            name="📌 Commandes",
            value=(
                "`/download type:[type] scope:[nombre ou 'all']`\n"
                "Télécharge les médias du type spécifié\n\n"
                "**Types disponibles :**\n"
                "• `images` - Photos\n"
                "• `videos` - Vidéos\n"
                "• `gifs` - GIFs\n"
                "• `all` - Tous les médias\n\n"
                "Nombres disponibles :\n"
                "• 10 - Messages\n"
                "• 100 - Messages\n"
                "• 1000... - Messages\n"
                "• Tous - Tous les messages"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💡 Exemples",
            value=(
                "`/download images 50` - 50 dernières images\n"
                "`/download videos Tous` - Toutes les vidéos\n"
                "`/download Tous Tous` - Tous les médias de tous les messages disponibles dans le canal"
            ),
            inline=False
        )
        
        embed.set_footer(text="Bot créé par Arthur")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="download", description="Télécharge les médias spécifiés")
    @app_commands.choices(
        type=[
            app_commands.Choice(name="Images", value="images"),
            app_commands.Choice(name="Vidéos", value="videos"),
            app_commands.Choice(name="GIFs", value="gifs"),
            app_commands.Choice(name="Tout", value="all")
        ],
        scope=[
            app_commands.Choice(name="Tout", value="all"),
            app_commands.Choice(name="10 derniers", value="10"),
            app_commands.Choice(name="50 derniers", value="50"),
            app_commands.Choice(name="100 derniers", value="100"),
            app_commands.Choice(name="500 derniers", value="500")
        ]
    )
    async def download_media(
        self, 
        interaction: discord.Interaction, 
        type: app_commands.Choice[str],
        scope: app_commands.Choice[str]
    ):
        await interaction.response.send_message("🔍 Recherche des médias...")
        status_message = await interaction.original_response()
        
        # Nettoyer le type de média
        clean_type = type.value
        type_key = f"📷 {clean_type}" if clean_type == 'images' else \
                  f"🎥 {clean_type}" if clean_type == 'videos' else \
                  f"🎞️ {clean_type}" if clean_type == 'gifs' else \
                  f"📁 {clean_type}"

        # Déterminer la limite de messages
        limit = None if scope.value == "all" else int(scope.value)

        # Message initial
        if limit:
            await status_message.edit(content=f"🔍 Recherche dans les {limit} derniers messages...")
        else:
            await status_message.edit(content="🔍 Recherche dans tous les messages du canal...")

        # Collecter les médias
        media_files = []
        total_size = 0
        processed_messages = 0
        
        async with interaction.channel.typing():
            async for message in interaction.channel.history(limit=limit):
                processed_messages += 1
                if processed_messages % 100 == 0:
                    await status_message.edit(content=f"🔍 Recherche en cours... ({processed_messages} messages analysés)")
                
                for attachment in message.attachments:
                    if self._is_valid_type(attachment.filename, type_key):
                        media_files.append(attachment)
                        total_size += attachment.size

        if not media_files:
            await status_message.edit(content=f"❌ Aucun média de type `{clean_type}` trouvé.")
            return

        try:
            # Créer les scripts
            batch_content = self._create_batch_script(media_files)
            shell_content = self._create_shell_script(media_files)

            # Créer un thread avec nom approprié
            thread_name = f"📥 Téléchargement {clean_type}"
            if limit:
                thread_name += f" ({limit} messages, {len(media_files)} fichiers)"
            else:
                thread_name += f" (tous les messages, {len(media_files)} fichiers)"

            thread = await interaction.channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.public_thread
            )

            # Envoyer les informations
            embed = discord.Embed(
                title="📥 Téléchargement prêt !",
                description="Choisissez le script selon votre système :",
                color=self.color
            )
            
            # Description du scope
            scope_desc = f"• Messages analysés : {processed_messages}\n"
            if limit:
                scope_desc += f"• Limite : {limit} messages\n"
            else:
                scope_desc += "• Scope : Canal entier\n"

            embed.add_field(
                name="📊 Résumé",
                value=(
                    scope_desc +
                    f"• Type : {type_key}\n"
                    f"• Fichiers trouvés : {len(media_files)}\n"
                    f"• Taille totale : {self._format_size(total_size)}"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🪟 Windows",
                value="1. Téléchargez `download.bat`\n2. Double-cliquez dessus",
                inline=True
            )
            
            embed.add_field(
                name="🐧 Linux/Mac",
                value="1. Téléchargez `download.sh`\n2. `chmod +x download.sh`\n3. `./download.sh`",
                inline=True
            )

            await thread.send(embed=embed)

            # Envoyer les scripts
            await thread.send(
                "📦 Scripts de téléchargement :",
                files=[
                    discord.File(io.BytesIO(batch_content.encode()), "download.bat"),
                    discord.File(io.BytesIO(shell_content.encode()), "download.sh")
                ]
            )

            # Mettre à jour le statut
            embed_status = discord.Embed(
                description=f"✅ Les scripts sont disponibles dans {thread.mention}",
                color=self.color
            )
            await status_message.edit(content=None, embed=embed_status)

        except Exception as e:
            await status_message.edit(content=f"❌ Une erreur est survenue : {str(e)}")
            if 'thread' in locals():
                await thread.delete()

    def _create_batch_script(self, media_files):
        """Crée le script batch Windows avec organisation automatique"""
        script = "@echo off\n"
        script += "echo 📥 Téléchargement et organisation des fichiers...\n"
        script += "cd %USERPROFILE%\\Desktop\n"
        script += "mkdir MediaDownload 2>nul\n"
        script += "cd MediaDownload\n"
        script += "mkdir Videos 2>nul\n"
        script += "mkdir Images 2>nul\n\n"

        # Grouper les fichiers par catégorie
        categories = {}
        for attachment in media_files:
            filename = attachment.filename.lower()
            # Détecter si c'est une vidéo ou une image
            if any(filename.endswith(ext) for ext in ['.mp4', '.mov', '.webm']):
                # Extraire le nom de la catégorie (avant le premier tiret ou underscore ou espace)
                category = next((
                    word.strip() for word in re.split(r'[-_\s]', filename)
                    if word.strip() and not any(ext in word for ext in ['.mp4', '.mov', '.webm'])
                ), 'autres')
                
                if category not in categories:
                    categories[category] = []
                categories[category].append(attachment)

        # Créer les dossiers et télécharger les fichiers
        total_files = len(media_files)
        current_file = 0

        for category, files in categories.items():
            script += f'mkdir "Videos\\{category}" 2>nul\n'
            for attachment in files:
                current_file += 1
                safe_filename = attachment.filename.replace(" ", "_")
                script += f'echo [{current_file}/{total_files}] {safe_filename}\n'
                script += f'curl -L -o "Videos\\{category}\\{safe_filename}" "{attachment.url}"\n'

        script += "\necho ✅ Téléchargement terminé !\n"
        script += "echo Les fichiers sont organisés dans le dossier MediaDownload sur votre bureau\n"
        script += "explorer .\n"  # Ouvre le dossier à la fin
        script += "pause"
        return script

    def _create_shell_script(self, media_files):
        """Crée le script shell Linux/Mac avec organisation automatique"""
        script = "#!/bin/bash\n"
        script += "echo '📥 Téléchargement et organisation des fichiers...'\n"
        script += "cd ~/Desktop\n"
        script += "mkdir -p MediaDownload\n"
        script += "cd MediaDownload\n"
        script += "mkdir -p Videos Images\n\n"

        # Grouper les fichiers par catégorie
        categories = {}
        for attachment in media_files:
            filename = attachment.filename.lower()
            # Détecter si c'est une vidéo ou une image
            if any(filename.endswith(ext) for ext in ['.mp4', '.mov', '.webm']):
                # Extraire le nom de la catégorie (avant le premier tiret ou underscore ou espace)
                category = next((
                    word.strip() for word in re.split(r'[-_\s]', filename)
                    if word.strip() and not any(ext in word for ext in ['.mp4', '.mov', '.webm'])
                ), 'autres')
                
                if category not in categories:
                    categories[category] = []
                categories[category].append(attachment)

        # Créer les dossiers et télécharger les fichiers
        total_files = len(media_files)
        current_file = 0

        for category, files in categories.items():
            script += f'mkdir -p "Videos/{category}"\n'
            for attachment in files:
                current_file += 1
                safe_filename = attachment.filename.replace(" ", "_")
                script += f'echo "[{current_file}/{total_files}] {safe_filename}"\n'
                script += f'curl -L -o "Videos/{category}/{safe_filename}" "{attachment.url}"\n'

        script += "\necho '✅ Téléchargement terminé !'\n"
        script += "echo 'Les fichiers sont organisés dans le dossier MediaDownload sur votre bureau'\n"
        script += "xdg-open . 2>/dev/null || open . 2>/dev/null || explorer.exe . 2>/dev/null"  # Ouvre le dossier à la fin
        return script

    def _is_valid_type(self, filename, type_key):
        """Vérifie si le fichier correspond au type demandé"""
        ext = os.path.splitext(filename.lower())[1]
        return ext in self.bot.media_types[type_key]

    def _format_size(self, size_bytes):
        """Formate la taille en format lisible"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"

async def main():
    async with MediaDownload() as bot:
        await bot.start(TOKEN)

# Lancer le bot
import asyncio
asyncio.run(main())