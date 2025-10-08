import discord
from discord.ext import commands
from discord import app_commands

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show bot help")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 Media Download Help",
            description="Here are all available commands:",
            color=0x3498db
        )
        
        embed.add_field(
            name="/download",
            value=(
                "Download media files with smart organization\n"
                "• Choose type: Images, Videos, or All\n"
                "• Choose number of messages to scan\n"
                "• 🧠 Automatic categorization by content\n"
                "• 📁 Organized folders (min 3 files per category)\n"
                "• Free: Up to 25MB direct download\n"
                "• Vote required: Unlimited size with Gofile.io"
            ),
            inline=False
        )
        
        embed.add_field(
            name="/bug",
            value="Report a bug to the developers",
            inline=False
        )
        
        embed.add_field(
            name="/suggest",
            value="Submit a suggestion for the bot",
            inline=False
        )
        
        embed.add_field(
            name="/stats",
            value="Show bot statistics",
            inline=False
        )
        
        embed.add_field(
            name="/test-classification",
            value="Test the smart file organization system",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(HelpCog(bot)) 