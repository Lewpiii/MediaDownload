import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import logging

# Configuration
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('bot')

class MediaDownloadBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        logger.info("Bot is setting up...")

    async def on_ready(self):
        logger.info(f"Bot is ready! Logged in as {self.user.name}")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers"
            )
        )

def run_bot():
    bot = MediaDownloadBot()
    try:
        logger.info("Starting bot...")
        bot.run(TOKEN, log_handler=None)
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    run_bot()