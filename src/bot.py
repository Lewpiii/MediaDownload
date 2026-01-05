import discord
from discord.ext import commands, tasks
import os
import asyncio
import logging
from datetime import datetime

# Import local modules
# Use relative imports assuming this runs as a module (python -m src.bot)
from .config import BOT_TOKEN, LOGS_CHANNEL_ID
from .utils.logging import Logger
from .utils.performance import performance_optimizer
from .utils.topgg_checker import TopGGChecker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger('bot.core')

class MediaDownloadBot(commands.Bot):
    def __init__(self):
        # Intents: Minimum required. No message_content needed.
        intents = discord.Intents.default()
        intents.message_content = False 
        
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None
        )
        
        self.last_status = True
        self.log_channel = None
        self.status_index = 0
        self.start_time = datetime.utcnow()
        self.logs_channel_id = LOGS_CHANNEL_ID

    async def setup_hook(self):
        """Initial bot configuration"""
        try:
            logger.info("Starting setup hook...")
            
            # Initialize Top.gg checker
            self.topgg_checker = TopGGChecker(self)
            
            # Apply performance optimizations
            await performance_optimizer.optimize_system()
            
            # Load cogs
            cogs_dir = os.path.join(os.path.dirname(__file__), 'cogs')
            if not os.path.exists(cogs_dir):
                logger.error(f"Cogs directory not found at {cogs_dir}")
                return

            logger.info("=== Loading Cogs ===")
            for filename in os.listdir(cogs_dir):
                if filename.endswith('.py') and not filename.startswith('__'):
                    try:
                        await self.load_extension(f'src.cogs.{filename[:-3]}')
                        logger.info(f"✓ Loaded: {filename}")
                    except Exception as e:
                        logger.error(f"✗ Failed to load {filename}: {e}")
            
            # Synchronize commands
            logger.info("Synchronizing commands...")
            try:
                synced = await self.tree.sync()
                logger.info(f"=== Registered {len(synced)} Commands ===")
                for cmd in synced:
                    logger.info(f"✓ /{cmd.name}")
            except Exception as e:
                logger.error(f"Failed to sync commands: {e}")
            
            # Start status rotation
            self.rotate_status.start()
            
            logger.info("Setup hook completed")
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}")
            raise

    @tasks.loop(minutes=5)
    async def rotate_status(self):
        """Change bot status every 5 minutes"""
        try:
            if self.status_index == 0:
                activity = discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"/help | {len(self.guilds)} servers"
                )
            else:
                total_users = sum(g.member_count for g in self.guilds)
                activity = discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"/help | {total_users} users"
                )
            
            await self.change_presence(status=discord.Status.online, activity=activity)
            self.status_index = (self.status_index + 1) % 2

        except Exception as e:
            logger.error(f"Error in rotate_status: {e}")

    @rotate_status.before_loop
    async def before_rotate_status(self):
        await self.wait_until_ready()

    async def on_ready(self):
        logger.info("=== Bot Ready ===")
        logger.info(f"Logged in as: {self.user.name} ({self.user.id})")
        logger.info(f"Guild count: {len(self.guilds)}")
        
        # Initialize log channel
        if self.logs_channel_id:
            try:
                self.log_channel = self.get_channel(self.logs_channel_id)
                if self.log_channel:
                    embed = discord.Embed(
                        title="🟢 Bot Online",
                        description="Bot has started successfully (Refactored)",
                        color=0x00FF00,
                        timestamp=datetime.utcnow()
                    )
                    await self.log_channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Failed to send startup log: {e}")

    async def on_guild_join(self, guild: discord.Guild):
        logger.info(f"Joined new server: {guild.name} ({guild.id})")
        # Removed webhook redundant logic for simplicity, relying on logs channel

def run():
    if not BOT_TOKEN:
        logger.critical("DISCORD_TOKEN not found!")
        return
        
    bot = MediaDownloadBot()
    bot.run(BOT_TOKEN, log_handler=None) # We configured our own logging

if __name__ == "__main__":
    run()