import os
import tempfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('DISCORD_TOKEN')
GOFILE_TOKEN = os.getenv('GOFILE_TOKEN')
TOP_GG_TOKEN = os.getenv('TOP_GG_TOKEN')

# Logs Channel
try:
    logs_channel_id = os.getenv('LOGS_CHANNEL_ID')
    LOGS_CHANNEL_ID = int(logs_channel_id) if logs_channel_id else None
except (ValueError, TypeError):
    LOGS_CHANNEL_ID = None

# Media Types
MEDIA_TYPES = {
    'images': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'],
    'videos': ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv'],
    'all': ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv']
}

# Limits
MAX_DIRECT_DOWNLOAD_SIZE = 25 * 1024 * 1024  # 25MB Discord limit
MAX_SINGLE_FILE_SIZE = 100 * 1024 * 1024     # 100MB max per file
MAX_TOTAL_DOWNLOAD_SIZE = 500 * 1024 * 1024  # 500MB max total

# Download Configuration
DOWNLOAD_CONFIG = {
    'temp_dir': os.path.join(tempfile.gettempdir(), 'discord_bot_media'),
    'chunk_size': 2 * 1024 * 1024,        # 2MB chunks
    'max_concurrent_downloads': 2,
    'cleanup_after_zip': True,
    'compress_level': 6,
    'max_retries': 3,
    'timeout_total': 300,
    'timeout_connect': 30,
    'timeout_read': 60,
    'progress_update_interval': 3
}

# Resource Limits
RESOURCE_LIMITS = {
    'memory_threshold': 85,  # %
    'disk_threshold': 90,    # %
    'pause_duration': 30     # seconds
}

# Categories
CATEGORIES = {
    # Games
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
    
    # Other
    'meme': 'Fun/Memes',
    'funny': 'Fun/Memes',
    'clip': 'Clips',
    'gameplay': 'Gameplay',
}