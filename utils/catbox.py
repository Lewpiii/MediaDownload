import aiohttp
from typing import Dict, List, Tuple
import discord
import zipfile
import io
import os
from datetime import datetime
from .ai_detector import MediaDetector

class CatboxUploader:
    def __init__(self):
        self.upload_url = "https://catbox.moe/user/api.php"
        self.media_types = {
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'],
            'videos': ['.mp4', '.webm', '.mov', '.avi', '.mkv']
        }

    async def organize_and_upload(self, media_files: Dict[str, List[discord.Attachment]], server_name: str = "Unknown") -> Tuple[Dict, str]:
        """Upload tous les fichiers dans un ZIP organisé"""
        try:
            # Initialiser les statistiques
            stats = {
                'total': 0,
                'total_size': 0,
                'types': {
                    'Images': {'size': 0, 'count': 0},
                    'Videos': {'size': 0, 'count': 0}
                }
            }

            # Télécharger et organiser les fichiers
            files_to_zip = []
            for file_type, files in media_files.items():
                for file in files:
                    print(f"Downloading: {file.filename}")
                    file_data = await file.read()
                    
                    # Mettre à jour les statistiques
                    file_size = len(file_data)
                    stats['total'] += 1
                    stats['total_size'] += file_size
                    
                    # Classifier par type
                    if file_type.lower() in [ext[1:] for ext in self.media_types['images']]:
                        stats['types']['Images']['count'] += 1
                        stats['types']['Images']['size'] += file_size
                    elif file_type.lower() in [ext[1:] for ext in self.media_types['videos']]:
                        stats['types']['Videos']['count'] += 1
                        stats['types']['Videos']['size'] += file_size
                    
                    files_to_zip.append((file.filename, file_data))
                    print(f"Downloaded {file.filename}")

            # Créer et uploader le ZIP
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_server_name = "".join(c for c in server_name if c.isalnum() or c in (' ', '-', '_')).strip()
            zip_filename = f"{safe_server_name}_media_{timestamp}.zip"
            
            print("Creating ZIP file...")
            zip_data = await self.create_zip(files_to_zip, timestamp)
            
            url = await self.upload_file(zip_data, zip_filename)
            
            return stats, url

        except Exception as e:
            print(f"Error in organize_and_upload: {e}")
            raise

    async def create_zip(self, files: List[Tuple[str, bytes]], timestamp: str) -> bytes:
        """Crée un fichier ZIP en mémoire"""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, content in files:
                zip_file.writestr(f"media_collection_{timestamp}/{filename}", content)
        return zip_buffer.getvalue()

    async def upload_file(self, file_data: bytes, filename: str) -> str:
        """Upload un fichier sur Catbox"""
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('reqtype', 'fileupload')
                data.add_field('userhash', '')
                data.add_field('fileToUpload', file_data, filename=filename)
                
                async with session.post(self.upload_url, data=data) as response:
                    if response.status == 200:
                        url = await response.text()
                        return url
                    raise Exception(f"Upload failed: {await response.text()}")
        except Exception as e:
            print(f"Error uploading file: {e}")
            raise 