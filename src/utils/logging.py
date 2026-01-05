import discord
from datetime import datetime
from typing import Optional
import os

class Logger:
    def __init__(self, bot):
        self.bot = bot
        self.log_channel_id = int(os.getenv('LOGS_CHANNEL_ID'))

    async def log_command(self, 
                         interaction: discord.Interaction, 
                         command_name: str, 
                         status: str = "Success",
                         error: Optional[Exception] = None):
        """Log l'utilisation d'une commande"""
        try:
            log_channel = self.bot.get_channel(self.log_channel_id)
            if not log_channel:
                return

            embed = discord.Embed(
                title=f"Command Used: /{command_name}",
                color=0x00FF00 if status == "Success" else 0xFF0000,
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="User",
                value=f"{interaction.user} (ID: {interaction.user.id})"
            )

            embed.add_field(
                name="Server",
                value=f"{interaction.guild.name} (ID: {interaction.guild.id})"
            )

            embed.add_field(
                name="Channel",
                value=f"{interaction.channel.name} (ID: {interaction.channel.id})"
            )

            embed.add_field(name="Status", value=status)

            if error:
                embed.add_field(
                    name="Error",
                    value=f"```{str(error)}```",
                    inline=False
                )

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"Error in logging: {e}")

    async def log_guild_join(self, guild: discord.Guild):
        """Log quand le bot rejoint un serveur"""
        try:
            log_channel = self.bot.get_channel(self.log_channel_id)
            if not log_channel:
                return

            embed = discord.Embed(
                title="📥 Bot Added to Server",
                description=f"Server: {guild.name}\nID: {guild.id}",
                color=0x00FF00,
                timestamp=datetime.utcnow()
            )

            embed.add_field(name="Members", value=str(guild.member_count))
            embed.add_field(name="Owner", value=str(guild.owner))
            embed.add_field(name="Created At", value=guild.created_at.strftime("%Y-%m-%d"))

            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"Error in guild join logging: {e}")

    async def log_guild_remove(self, guild: discord.Guild):
        """Log quand le bot quitte un serveur"""
        try:
            log_channel = self.bot.get_channel(self.log_channel_id)
            if not log_channel:
                return

            embed = discord.Embed(
                title="📤 Bot Removed from Server",
                description=f"Server: {guild.name}\nID: {guild.id}",
                color=0xFF0000,
                timestamp=datetime.utcnow()
            )

            embed.add_field(name="Members", value=str(guild.member_count))
            embed.add_field(name="Owner", value=str(guild.owner))
            embed.add_field(name="Created At", value=guild.created_at.strftime("%Y-%m-%d"))

            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"Error in guild remove logging: {e}") 