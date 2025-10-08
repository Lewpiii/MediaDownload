import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stats", description="Show bot statistics and performance metrics")
    async def stats(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📊 Bot Statistics",
            description="Current bot performance and usage statistics",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )
        
        # Server statistics
        embed.add_field(
            name="🌐 Servers",
            value=f"**{len(self.bot.guilds)}** servers",
            inline=True
        )
        
        # Total users
        total_members = sum(g.member_count for g in self.bot.guilds)
        embed.add_field(
            name="👥 Users",
            value=f"**{total_members:,}** total users",
            inline=True
        )
        
        # Bot latency
        embed.add_field(
            name="⚡ Latency",
            value=f"**{round(self.bot.latency * 1000)}ms**",
            inline=True
        )
        
        # Commands available
        embed.add_field(
            name="🔧 Commands",
            value="**6** commands available",
            inline=True
        )
        
        # Library version
        embed.add_field(
            name="📚 Library",
            value="**discord.py** v2.0+",
            inline=True
        )
        
        # Uptime (approximate)
        uptime = datetime.utcnow() - self.bot.start_time if hasattr(self.bot, 'start_time') else timedelta(seconds=0)
        embed.add_field(
            name="⏱️ Uptime",
            value=f"**{str(uptime).split('.')[0]}**",
            inline=True
        )
        
        # Features
        embed.add_field(
            name="🚀 Features",
            value=(
                "• **Interactive Menus**: Button-based interface\n"
                "• **Smart Organization**: Auto-categorization\n"
                "• **SSD Optimization**: Direct disk writes\n"
                "• **Resource Monitoring**: Auto-pause protection\n"
                "• **Large File Support**: External hosting\n"
                "• **Progress Tracking**: Real-time updates"
            ),
            inline=False
        )
        
        embed.set_footer(text="Bot is running smoothly! 🎉")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(StatsCog(bot)) 