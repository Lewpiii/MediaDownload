import discord
from discord.ext import commands
from discord import app_commands

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show bot help and available commands")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 Media Download Bot Help",
            description="Welcome to the Media Download Bot! Here are all available commands:",
            color=0x3498db
        )
        
        embed.add_field(
            name="/download",
            value=(
                "🎯 **Interactive Download Menu**\n"
                "• Open a user-friendly interface with buttons\n"
                "• Choose date ranges (Last hour, Today, This week, etc.)\n"
                "• Select media types (Images, Videos, All)\n"
                "• 🧠 Automatic smart organization\n"
                "• 📁 Folders created for categories with 3+ files\n"
                "• ⚡ SSD-optimized downloads (no RAM usage)\n"
                "• 📊 Real-time progress updates"
            ),
            inline=False
        )
        
        embed.add_field(
            name="/test-classification",
            value=(
                "🧠 **Test Smart Organization**\n"
                "• Test the intelligent file categorization system\n"
                "• See how files would be organized\n"
                "• View category statistics and folder structure"
            ),
            inline=False
        )
        
        embed.add_field(
            name="/bug",
            value=(
                "🐛 **Report Issues**\n"
                "• Report bugs or problems to developers\n"
                "• Help improve the bot with your feedback"
            ),
            inline=False
        )
        
        embed.add_field(
            name="/suggest",
            value=(
                "💡 **Submit Suggestions**\n"
                "• Suggest new features or improvements\n"
                "• Share ideas for better functionality"
            ),
            inline=False
        )
        
        embed.add_field(
            name="/stats",
            value=(
                "📊 **Bot Statistics**\n"
                "• View bot performance metrics\n"
                "• See server count and user statistics\n"
                "• Check bot latency and uptime"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🚀 Key Features",
            value=(
                "• **Smart Organization**: Files automatically sorted by category\n"
                "• **Interactive Interface**: Easy-to-use button menus\n"
                "• **Resource Monitoring**: Automatic pausing if system overloaded\n"
                "• **SSD Optimization**: Direct disk writes, no RAM usage\n"
                "• **Large File Support**: External hosting for files >25MB\n"
                "• **Progress Tracking**: Real-time download progress"
            ),
            inline=False
        )
        
        embed.set_footer(text="Click /download to start downloading media files!")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(HelpCog(bot)) 