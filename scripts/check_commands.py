#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnostic simple pour vérifier les commandes du bot
"""

import asyncio
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

async def check_commands():
    """Vérifier les commandes disponibles"""
    print("=== Vérification des Commandes du Bot ===")
    print()
    
    # Créer un bot de test
    intents = discord.Intents.default()
    intents.guilds = True
    # Note: message_content retiré car non nécessaire pour les slash commands
    
    bot = commands.Bot(
        command_prefix=commands.when_mentioned,
        intents=intents,
        help_command=None
    )
    
    @bot.event
    async def on_ready():
        print(f"Bot connecté: {bot.user}")
        print()
        
        # Charger le cog download
        try:
            await bot.load_extension('cogs.download')
            print("OK: Cog download charge")
        except Exception as e:
            print(f"ERREUR chargement cog download: {e}")
            print("   Détails de l'erreur:")
            import traceback
            traceback.print_exc()
            return
        
        # Synchroniser les commandes
        try:
            synced = await bot.tree.sync()
            print(f"OK: {len(synced)} commandes synchronisees")
            
            # Lister les commandes
            print()
            print("Commandes disponibles:")
            commands = await bot.tree.fetch_commands()
            for cmd in commands:
                print(f"  - /{cmd.name}: {cmd.description}")
            
            if not commands:
                print("  ATTENTION: Aucune commande trouvee")
            
        except Exception as e:
            print(f"ERREUR synchronisation: {e}")
        
        # Fermer le bot
        await bot.close()
    
    # Démarrer le bot
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("ERREUR: Token Discord non trouve")
        print("ASTUCE: Verifiez votre fichier .env ou vos GitHub Secrets")
        return
    
    try:
        await bot.start(token)
    except Exception as e:
        print(f"ERREUR demarrage: {e}")

if __name__ == "__main__":
    asyncio.run(check_commands())
