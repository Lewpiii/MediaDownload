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

class TopGGChecker:
    """Gestionnaire de vérification des votes top.gg"""
    
    def __init__(self, bot):
        self.bot = bot
        self.token = TOP_GG_TOKEN
        self.api_url = "https://top.gg/api"
        
    async def has_voted(self, user_id: int) -> bool:
        """
        Vérifie si un utilisateur a voté sur top.gg dans les dernières 12h
        
        Args:
            user_id: L'ID Discord de l'utilisateur
            
        Returns:
            True si l'utilisateur a voté, False sinon
        """
        if not self.token:
            logger.warning("TOP_GG_TOKEN not configured, skipping vote check")
            return True  # Si pas de token, on autorise tout le monde
            
        try:
            headers = {
                'Authorization': self.token
            }
            
            url = f"{self.api_url}/bots/{self.bot.user.id}/check?userId={user_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        # L'API retourne {"voted": 1} si l'utilisateur a voté dans les 12h
                        return data.get('voted', 0) == 1
                    else:
                        logger.error(f"Top.gg API error: {response.status}")
                        return True  # En cas d'erreur API, on autorise
                        
        except Exception as e:
            logger.error(f"Error checking vote status: {e}")
            return True  # En cas d'erreur, on autorise
    
    async def create_vote_embed(self) -> discord.Embed:
        """Crée un embed demandant à l'utilisateur de voter"""
        embed = discord.Embed(
            title="🗳️ Vote requis !",
            description=(
                "Pour utiliser cette commande, vous devez d'abord voter pour le bot sur **top.gg**.\n\n"
                "C'est **gratuit** et ne prend que **quelques secondes** !\n"
                "Votre vote nous aide énormément à faire connaître le bot. 💙"
            ),
            color=0xFF6B6B,
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="✨ Avantages",
            value=(
                "• Accès à toutes les commandes de téléchargement\n"
                "• Organisation intelligente des fichiers\n"
                "• Téléchargements illimités pendant 12h\n"
                "• Support du bot et développement de nouvelles fonctionnalités"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📝 Comment voter ?",
            value=(
                "1. Cliquez sur le lien ci-dessous\n"
                "2. Connectez-vous avec votre compte Discord\n"
                "3. Cliquez sur le bouton **Vote**\n"
                "4. Revenez ici et réessayez la commande !"
            ),
            inline=False
        )
        
        embed.set_footer(text="Le vote dure 12 heures • Merci de votre soutien !")
        
        return embed
    
    def get_vote_button(self) -> discord.ui.View:
        """Crée un bouton pour voter sur top.gg"""
        view = discord.ui.View()
        button = discord.ui.Button(
            label="🗳️ Voter sur top.gg",
            style=discord.ButtonStyle.link,
            url=f"https://top.gg/bot/{self.bot.user.id}/vote",
            emoji="🗳️"
        )
        view.add_item(button)
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

