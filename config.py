import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration du bot
BOT_TOKEN = os.getenv('DISCORD_TOKEN')
GOFILE_TOKEN = os.getenv('GOFILE_TOKEN')
TOP_GG_TOKEN = os.getenv('TOP_GG_TOKEN')

# Assurez-vous que LOGS_CHANNEL_ID est un int
try:
    LOGS_CHANNEL_ID = int(os.getenv('LOGS_CHANNEL_ID'))
except (ValueError, TypeError):
    raise ValueError("LOGS_CHANNEL_ID must be a valid integer in .env file")

# Configuration des médias
MEDIA_TYPES = {
    'images': ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
    'videos': ['.mp4', '.webm', '.mov'],
    'all': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.webm', '.mov']
}

# Limites
MAX_DIRECT_DOWNLOAD_SIZE = 25 * 1024 * 1024  # 25MB

# Configuration des catégories
CATEGORIES = {
    # Jeux
    'valorant': 'Games/Valorant',
    'minecraft': 'Games/Minecraft',
    'fortnite': 'Games/Fortnite',
    'csgo': 'Games/CS',
    'cs2': 'Games/CS',
    'lol': 'Games/LeagueOfLegends',
    'league': 'Games/LeagueOfLegends',
    'apex': 'Games/ApexLegends',
    'rocket': 'Games/RocketLeague',
    
    # Apps
    'discord': 'Apps/Discord',
    'photoshop': 'Apps/Photoshop',
    'premiere': 'Apps/Premiere',
    
    # Autres
    'meme': 'Fun/Memes',
    'funny': 'Fun/Memes',
    'clip': 'Clips',
    'gameplay': 'Gameplay',
} 