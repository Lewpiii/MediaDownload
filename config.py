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
    logs_channel_id = os.getenv('LOGS_CHANNEL_ID')
    LOGS_CHANNEL_ID = int(logs_channel_id) if logs_channel_id else None
except (ValueError, TypeError):
    LOGS_CHANNEL_ID = None

# Configuration des médias
MEDIA_TYPES = {
    'images': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'],
    'videos': ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv'],
    'all': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv']
}

# Limites
MAX_DIRECT_DOWNLOAD_SIZE = 25 * 1024 * 1024  # 25MB Discord limit
MAX_SINGLE_FILE_SIZE = 100 * 1024 * 1024     # 100MB max per file
MAX_TOTAL_DOWNLOAD_SIZE = 500 * 1024 * 1024  # 500MB max total

# Configuration des téléchargements (SSD optimisé)
DOWNLOAD_CONFIG = {
    'temp_dir': '/tmp/discord_downloads',  # Dossier temporaire sur SSD
    'chunk_size': 8 * 1024 * 1024,        # 8MB chunks pour streaming
    'max_concurrent_downloads': 3,          # Limite les téléchargements simultanés
    'cleanup_after_zip': True,              # Supprime les fichiers après ZIP
    'compress_level': 6                     # Niveau de compression ZIP (1-9)
}

# Configuration des ressources
RESOURCE_LIMITS = {
    'memory_threshold': 85,  # % d'utilisation mémoire max
    'disk_threshold': 90,    # % d'utilisation disque max
    'pause_duration': 30     # Secondes de pause si limite atteinte
}

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