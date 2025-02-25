from discord.ext import commands
import discord
from typing import Dict, List
import os

class Media(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("✓ Media cog loaded")

    @commands.command(name='dl')
    async def download(self, ctx):
        """Télécharge les médias du message"""
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

            # Message de chargement
            loading_msg = await ctx.send("⏳ Téléchargement en cours...")

            # Organiser les fichiers par type
            media_files: Dict[str, List[discord.Attachment]] = {}
            for attachment in attachments:
                file_type = attachment.filename.split('.')[-1].lower()
                if file_type not in media_files:
                    media_files[file_type] = []
                media_files[file_type].append(attachment)

            # Upload les fichiers
            download_url = await self.uploader.organize_and_upload(media_files)

            # Envoyer le lien de téléchargement
            await loading_msg.edit(content=f"✅ Téléchargement terminé !\n📥 {download_url}")

        except Exception as e:
            await ctx.send(f"❌ Une erreur est survenue: {str(e)}")
            print(f"Error in download command: {e}")

async def setup(bot):
    await bot.add_cog(Media(bot)) 