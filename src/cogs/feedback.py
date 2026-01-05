import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import os

class FeedbackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="bug", description="Report a bug or issue with the bot")
    async def bug(self, interaction: discord.Interaction, description: str):
        log_channel = self.bot.get_channel(int(os.getenv('LOGS_CHANNEL_ID')))
        
        embed = discord.Embed(
            title="🐛 Bug Report",
            description=description,
            color=0xFF0000,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="👤 Reported by",
            value=f"{interaction.user} (ID: {interaction.user.id})",
            inline=False
        )
        
        embed.add_field(
            name="🌐 Server",
            value=f"{interaction.guild.name} (ID: {interaction.guild.id})",
            inline=True
        )
        
        embed.add_field(
            name="📺 Channel",
            value=f"{interaction.channel.name} (ID: {interaction.channel.id})",
            inline=True
        )
        
        if log_channel:
            await log_channel.send(embed=embed)
        
        await interaction.response.send_message(
            "✅ Bug report sent! Thank you for helping improve the bot.",
            ephemeral=True
        )

    @app_commands.command(name="suggest", description="Submit a suggestion or feature request")
    async def suggest(self, interaction: discord.Interaction, suggestion: str):
        log_channel = self.bot.get_channel(int(os.getenv('LOGS_CHANNEL_ID')))
        
        embed = discord.Embed(
            title="💡 Feature Suggestion",
            description=suggestion,
            color=0x00FF00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="👤 Suggested by",
            value=f"{interaction.user} (ID: {interaction.user.id})",
            inline=False
        )
        
        embed.add_field(
            name="🌐 Server",
            value=f"{interaction.guild.name} (ID: {interaction.guild.id})",
            inline=True
        )
        
        embed.add_field(
            name="📺 Channel",
            value=f"{interaction.channel.name} (ID: {interaction.channel.id})",
            inline=True
        )
        
        if log_channel:
            await log_channel.send(embed=embed)
        
        await interaction.response.send_message(
            "✅ Suggestion sent! Thank you for your feedback and ideas.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(FeedbackCog(bot)) 