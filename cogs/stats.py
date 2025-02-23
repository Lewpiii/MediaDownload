import discord
from discord.ext import commands
from discord import app_commands

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stats", description="Show bot statistics")
    async def stats(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📊 Bot Statistics",
            color=0x3498db
        )
        
        # Statistiques des serveurs
        embed.add_field(
            name="Servers",
            value=str(len(self.bot.guilds)),
            inline=True
        )
        
        # Nombre total d'utilisateurs
        total_members = sum(g.member_count for g in self.bot.guilds)
        embed.add_field(
            name="Users",
            value=str(total_members),
            inline=True
        )
        
        # Latence du bot
        embed.add_field(
            name="Latency",
            value=f"{round(self.bot.latency * 1000)}ms",
            inline=True
        )
        
        # Uptime et autres stats
        embed.add_field(
            name="Commands",
            value="4 commands available",
            inline=True
        )
        
        embed.add_field(
            name="Library",
            value="discord.py",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(StatsCog(bot)) 