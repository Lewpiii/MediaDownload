"""
Top.gg Vote Checker
Vérifie si un utilisateur a voté sur top.gg avant d'utiliser certaines commandes
"""
import discord
from discord.ext import commands
import aiohttp
import logging
from functools import wraps
from config import TOP_GG_TOKEN

logger = logging.getLogger('bot.topgg')

class VoteView(discord.ui.View):
    """View with vote buttons and automatic verification"""
    
    def __init__(self, checker, download_options=None):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.checker = checker
        self.download_options = download_options
        self.auto_check_task = None
        self.start_auto_check()
    
    @discord.ui.button(label="🔄 Check Vote Status", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def check_vote_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Check if user has voted and proceed with download if yes"""
        print(f"[DEBUG] Vote status check clicked by {interaction.user.name}")
        
        # Update button to show checking
        button.label = "⏳ Checking..."
        button.disabled = True
        await interaction.response.edit_message(view=self)
        
        # Check vote status
        has_voted = await self.checker.has_voted(interaction.user.id)
        print(f"[DEBUG] Vote check result: {has_voted}")
        
        if has_voted:
            # User has voted! Show success and start download
            success_embed = discord.Embed(
                title="✅ Vote Confirmed!",
                description="Thank you for voting! Starting your download now...",
                color=0x00FF00,
                timestamp=discord.utils.utcnow()
            )
            success_embed.add_field(
                name="🎉 Benefits Active",
                value=(
                    "• Unlimited downloads for 12 hours\n"
                    "• Smart file organization\n"
                    "• Priority support\n"
                    "• Thank you for supporting the bot!"
                ),
                inline=False
            )
            success_embed.set_footer(text="Download starting...")
            
            await interaction.edit_original_response(embed=success_embed, view=None)
            
            # Start the download automatically
            if self.download_options:
                print(f"[DEBUG] Starting automatic download with options: {self.download_options}")
                from cogs.download import Download
                download_cog = interaction.client.get_cog('Download')
                if download_cog:
                    await download_cog.start_interactive_download(interaction, self.download_options)
                else:
                    await interaction.followup.send("❌ Download system not available.", ephemeral=True)
        else:
            # User hasn't voted yet
            button.label = "🔄 Check Vote Status"
            button.disabled = False
            
            not_voted_embed = discord.Embed(
                title="⏳ Vote Not Found",
                description=(
                    "We couldn't find your vote yet. This can happen if:\n\n"
                    "• You haven't voted yet\n"
                    "• You voted but it hasn't been processed yet (wait 1-2 minutes)\n"
                    "• There was an issue with the vote detection\n\n"
                    "Please make sure you've voted and try again in a moment!"
                ),
                color=0xFFA500,
                timestamp=discord.utils.utcnow()
            )
            not_voted_embed.set_footer(text="Try again in a few moments")
            
            await interaction.edit_original_response(embed=not_voted_embed, view=self)
    
    def start_auto_check(self):
        """Start automatic vote checking every 10 seconds"""
        import asyncio
        
        async def auto_check():
            await asyncio.sleep(10)  # Wait 10 seconds before first check
            # This will be implemented to automatically check and update
            pass
        
        # Start the task
        try:
            loop = asyncio.get_event_loop()
            self.auto_check_task = loop.create_task(auto_check())
        except:
            pass  # Ignore if we can't create the task
    
    async def on_timeout(self):
        """Called when the view times out"""
        if self.auto_check_task:
            self.auto_check_task.cancel()

class TopGGChecker:
    """Gestionnaire de vérification des votes top.gg"""
    
    def __init__(self, bot):
        self.bot = bot
        self.token = TOP_GG_TOKEN
        self.api_url = "https://top.gg/api"
        print(f"[DEBUG] TopGGChecker initialized with token: {'Yes' if self.token else 'No'}")
        print(f"[DEBUG] Bot ID: {bot.user.id if bot.user else 'Not ready'}")
        
    async def has_voted(self, user_id: int) -> bool:
        """
        Vérifie si un utilisateur a voté sur top.gg dans les dernières 12h
        
        Args:
            user_id: L'ID Discord de l'utilisateur
            
        Returns:
            True si l'utilisateur a voté, False sinon
        """
        print(f"[DEBUG] Checking vote for user {user_id}")
        
        if not self.token:
            print("[DEBUG] TOP_GG_TOKEN not configured, allowing access")
            logger.warning("TOP_GG_TOKEN not configured, skipping vote check")
            return True  # Si pas de token, on autorise tout le monde
            
        try:
            headers = {
                'Authorization': self.token
            }
            
            url = f"{self.api_url}/bots/{self.bot.user.id}/check?userId={user_id}"
            print(f"[DEBUG] Making API request to: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    print(f"[DEBUG] API response status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"[DEBUG] API response data: {data}")
                        # L'API retourne {"voted": 1} si l'utilisateur a voté dans les 12h
                        voted = data.get('voted', 0) == 1
                        print(f"[DEBUG] User voted status: {voted}")
                        return voted
                    else:
                        print(f"[DEBUG] API error: {response.status}")
                        logger.error(f"Top.gg API error: {response.status}")
                        return True  # En cas d'erreur API, on autorise
                        
        except Exception as e:
            print(f"[DEBUG] Exception in vote check: {e}")
            logger.error(f"Error checking vote status: {e}")
            return True  # En cas d'erreur, on autorise
    
    async def create_vote_embed(self) -> discord.Embed:
        """Creates an embed asking the user to vote"""
        embed = discord.Embed(
            title="🗳️ Vote Required!",
            description=(
                "To use this feature, you need to **vote for the bot** on **top.gg** first.\n\n"
                "It's **completely free** and takes only **a few seconds**!\n"
                "Your vote helps us tremendously to grow and improve the bot. 💙"
            ),
            color=0xFF6B6B,
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="✨ Benefits",
            value=(
                "• Access to all download commands\n"
                "• Smart file organization\n"
                "• Unlimited downloads for 12 hours\n"
                "• Support bot development and new features"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📝 How to vote?",
            value=(
                "1. Click the button below\n"
                "2. Login with your Discord account\n"
                "3. Click the **Vote** button\n"
                "4. Come back here and try again!"
            ),
            inline=False
        )
        
        embed.set_footer(text="Vote lasts 12 hours • Thank you for your support!")
        
        return embed
    
    def get_vote_button(self, download_options=None) -> discord.ui.View:
        """Creates vote buttons with automatic verification"""
        view = VoteView(self, download_options)
        
        # Vote button
        vote_button = discord.ui.Button(
            label="🗳️ Vote on top.gg",
            style=discord.ButtonStyle.link,
            url=f"https://top.gg/bot/{self.bot.user.id}/vote",
            emoji="🗳️"
        )
        view.add_item(vote_button)
        
        # Check vote status button
        check_button = discord.ui.Button(
            label="🔄 Check Vote Status",
            style=discord.ButtonStyle.secondary,
            emoji="🔄"
        )
        view.add_item(check_button)
        
        return view


def require_vote():
    """
    Décorateur pour vérifier si l'utilisateur a voté avant d'exécuter une commande
    
    Usage:
        @app_commands.command()
        @require_vote()
        async def my_command(self, interaction):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            # Vérifier si le bot a un checker top.gg
            checker = getattr(self.bot, 'topgg_checker', None)
            
            if not checker:
                # Si pas de checker configuré, autoriser la commande
                return await func(self, interaction, *args, **kwargs)
            
            # Vérifier si l'utilisateur a voté
            has_voted = await checker.has_voted(interaction.user.id)
            
            if has_voted:
                # L'utilisateur a voté, exécuter la commande normalement
                return await func(self, interaction, *args, **kwargs)
            else:
                # L'utilisateur n'a pas voté, afficher le message de vote
                embed = await checker.create_vote_embed()
                view = checker.get_vote_button()
                await interaction.response.send_message(
                    embed=embed,
                    view=view,
                    ephemeral=True
                )
                return None
        
        return wrapper
    return decorator

