import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
from datetime import datetime
import asyncio
import aiohttp
from counters import download_count, successful_downloads, failed_downloads
from dotenv import load_dotenv
from pathlib import Path
from utils.logging import Logger
from utils.catbox import CatboxUploader
import logging

# Configuration
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
LOGS_CHANNEL_ID = os.getenv('LOGS_CHANNEL_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
GOFILE_TOKEN = os.getenv('GOFILE_TOKEN')
TOP_GG_TOKEN = os.getenv('TOP_GG_TOKEN')

# Debug
print("\n=== Debug Discord Bot ===")
print(f"Token exists: {'Yes' if TOKEN else 'No'}")
print(f"Logs Channel ID: {LOGS_CHANNEL_ID}")
print(f"Webhook URL exists: {'Yes' if WEBHOOK_URL else 'No'}")
print("=======================\n")

if not TOKEN:
    raise ValueError("❌ Discord Token not found!")

try:
    LOGS_CHANNEL_ID = int(LOGS_CHANNEL_ID) if LOGS_CHANNEL_ID else None
except ValueError as e:
    print(f"❌ Error converting channel IDs: {e}")

# Configurer le logger
logger = None

# Configuration du logging plus détaillé
logging.basicConfig(
    level=logging.DEBUG,  # Changez en DEBUG pour plus de détails
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Définir l'intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

logging.info(f"Token trouvé : {'✓' if os.getenv('DISCORD_TOKEN') else '✗'}")

class MediaDownloadBot(commands.Bot):
    def __init__(self):
        print("\n=== Debug Discord Bot ===")
        print(f"Token exists: {'Yes' if os.getenv('DISCORD_TOKEN') else 'No'}")
        print(f"Logs Channel ID: {os.getenv('LOGS_CHANNEL_ID')}")
        print(f"Webhook URL exists: {'Yes' if os.getenv('WEBHOOK_URL') else 'No'}")
        print("=======================\n")
        
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None
        )
        
        # Initialiser les variables
        self.media_types = {
            'images': ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
            'videos': ['.mp4', '.webm', '.mov'],
            'all': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.webm', '.mov']
        }
        self.last_status = True
        self.log_channel = None
        self.status_task = None
        self.status_index = 0
        self.log_webhook_url = os.getenv('LOG_WEBHOOK_URL')

    async def setup_hook(self):
        """Configuration initiale du bot"""
        try:
            logging.info("Starting setup hook...")
            
            # Charger les cogs
            if not os.path.exists('./cogs'):
                os.makedirs('./cogs')
                logging.info("Created cogs directory")
            
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py') and not filename.startswith('__'):
                    try:
                        await self.load_extension(f'cogs.{filename[:-3]}')
                        logging.info(f"✓ Loaded cog: {filename}")
                    except Exception as e:
                        logging.error(f"✗ Failed to load {filename}: {e}")
            
            # Démarrer la rotation du statut après le chargement des cogs
            try:
                self.rotate_status.start()
                logging.info("✓ Started status rotation")
            except Exception as e:
                logging.error(f"✗ Failed to start status rotation: {e}")
            
            logging.info("Setup hook completed")
        except Exception as e:
            logging.error(f"Error in setup_hook: {e}")
            raise  # Relève l'erreur pour voir la stack trace complète

    @tasks.loop(minutes=5)
    async def rotate_status(self):
        """Change le statut du bot toutes les 5 minutes"""
        try:
            if self.status_index == 0:
                activity = discord.Activity(
                    type=discord.ActivityType.watching,  # En minuscules
                    name=f"/help | {len(self.guilds)} servers"
                )
                await self.change_presence(
                    status=discord.Status.online,
                    activity=activity
                )
            else:
                total_users = sum(g.member_count for g in self.guilds)
                activity = discord.Activity(
                    type=discord.ActivityType.watching,  # En minuscules
                    name=f"/help | {total_users} users"
                )
                await self.change_presence(
                    status=discord.Status.online,
                    activity=activity
                )
            
            self.status_index = (self.status_index + 1) % 2

        except Exception as e:
            print(f"Error in rotate_status: {e}")

    @rotate_status.before_loop
    async def before_rotate_status(self):
        """Attendre que le bot soit prêt avant de démarrer la rotation"""
        await self.wait_until_ready()

    async def on_ready(self):
        """Événement appelé quand le bot est prêt"""
        try:
            logging.info(f'Bot connecté en tant que {self.user.name}')
            
            # Définir le statut initial
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"/help | {len(self.guilds)} servers"
            )
            await self.change_presence(status=discord.Status.online, activity=activity)
            
            # Initialiser le channel de logs
            if logs_channel_id := os.getenv('LOGS_CHANNEL_ID'):
                self.log_channel = self.get_channel(int(logs_channel_id))
                if self.log_channel:
                    embed = discord.Embed(
                        title="🟢 Bot Online",
                        description="Bot has started successfully!",
                        color=0x00FF00,
                        timestamp=datetime.utcnow()
                    )
                    await self.log_channel.send(embed=embed)
            
            # Synchroniser les commandes
            await self.sync_commands()
            
            logging.info('Initialisation terminée')
        except Exception as e:
            logging.error(f'Erreur lors de l\'initialisation: {e}')

    async def status_check(self):
        """Vérifie périodiquement l'état du bot"""
        await self.wait_until_ready()
        
        while not self.is_closed():
            try:
                if not self.log_channel:
                    self.log_channel = self.get_channel(int(os.getenv('LOGS_CHANNEL_ID')))
                
                if self.log_channel:
                    latency = round(self.latency * 1000)
                    guilds = len(self.guilds)
                    
                    if not self.last_status:  # Si le bot était down avant
                        embed = discord.Embed(
                            title="✅ Bot Recovery",
                            description=(
                                "Bot is back online!\n"
                                f"Latency: {latency}ms\n"
                                f"Servers: {guilds}"
                            ),
                            color=0xFFAA00,
                            timestamp=datetime.utcnow()
                        )
                        await self.log_channel.send(embed=embed)
                    
                    self.last_status = True
                
            except Exception as e:
                if self.last_status:  # Si le bot était up avant
                    try:
                        embed = discord.Embed(
                            title="🔴 Bot Offline",
                            description=f"Bot is experiencing issues\nError: {str(e)}",
                            color=0xFF0000,
                            timestamp=datetime.utcnow()
                        )
                        await self.log_channel.send(embed=embed)
                    except:
                        print(f"Failed to send offline status: {e}")
                    self.last_status = False
            
            await asyncio.sleep(300)  # Check every 5 minutes

    async def on_guild_join(self, guild: discord.Guild):
        """Envoie un message détaillé quand le bot rejoint un serveur"""
        try:
            # Créer un embed riche
            embed = discord.Embed(
                title="🎉 Bot Added to New Server!",
                description=f"**{self.user.name}** has been added to a new server!",
                color=0x2ECC71,
                timestamp=datetime.utcnow()
            )

            # Informations sur le serveur
            embed.add_field(
                name="Server Info",
                value=f"""
                **Name:** {guild.name}
                **ID:** {guild.id}
                **Owner:** {guild.owner}
                **Members:** {guild.member_count}
                **Created:** <t:{int(guild.created_at.timestamp())}:R>
                """,
                inline=False
            )

            # Statistiques du bot
            embed.add_field(
                name="Bot Stats",
                value=f"""
                **Server Count:** {len(self.guilds)}
                **Total Users:** {sum(g.member_count for g in self.guilds)}
                """,
                inline=False
            )

            # Ajouter l'icône du serveur
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)

            # Envoyer via webhook si configuré
            if self.log_webhook_url:
                async with aiohttp.ClientSession() as session:
                    webhook = discord.Webhook.from_url(
                        self.log_webhook_url,
                        session=session
                    )
                    await webhook.send(embed=embed)
            
            # Sinon, envoyer dans le canal de logs si configuré
            elif logs_channel_id := os.getenv('LOGS_CHANNEL_ID'):
                channel = self.get_channel(int(logs_channel_id))
                if channel:
                    await channel.send(embed=embed)

            print(f"✓ Joined server: {guild.name} (ID: {guild.id})")

        except Exception as e:
            print(f"Error in on_guild_join: {e}")

    async def on_guild_remove(self, guild):
        """Quand le bot quitte un serveur"""
        if self.log_channel:
            embed = discord.Embed(
                title="📤 Bot Removed from Server",
                description=f"Server: {guild.name}\nID: {guild.id}",
                color=0xFF0000,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Members", value=str(guild.member_count))
            embed.add_field(name="Owner", value=str(guild.owner))
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            await self.log_channel.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx):
        """Sync the application commands"""
        try:
            synced = await self.tree.sync()
            await ctx.send(f"Synced {len(synced)} commands!")
        except Exception as e:
            await ctx.send(f"Failed to sync commands: {e}")

    async def sync_commands(self):
        """Synchronize commands with Discord"""
        try:
            print("Syncing commands...")
            
            # Sync commands to a specific guild
            guild = discord.Object(id=1333107536899084372)  # Ton ID de serveur
            
            # Ajouter une commande de test directement
            @self.tree.command(name="testping", description="Test if commands are working")
            async def testping(interaction: discord.Interaction):
                await interaction.response.send_message("Test command works!")
            
            # Sync commands
            guild_synced = await self.tree.sync(guild=guild)
            print(f"Successfully synced {len(guild_synced)} guild commands!")
            
            # List all commands
            print("\nAvailable commands:")
            for cmd in self.tree.get_commands(guild=guild):
                print(f"- /{cmd.name}")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
            import traceback
            traceback.print_exc()

def run_bot():
    """Démarrer le bot"""
    bot = MediaDownloadBot()
    try:
        logging.info("Starting bot...")
        bot.run(os.getenv('DISCORD_TOKEN'), log_handler=None)
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_bot()