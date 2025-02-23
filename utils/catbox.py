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
        self.detector = MediaDetector()
        self.media_types = {
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'],
            'videos': ['.mp4', '.webm', '.mov', '.avi', '.mkv']
        }

    async def analyze_and_sort_file(self, file_data: bytes, filename: str) -> Tuple[str, str, str]:
        """Analyse et détermine le chemin de classement du fichier"""
        # Déterminer le type principal (Image/Video)
        ext = os.path.splitext(filename.lower())[1]
        main_type = 'Images' if ext in self.media_types['images'] else 'Videos'
        
        # Analyser avec l'IA
        detection = await self.detector.analyze_media(file_data, filename)
        
        # Construire le chemin
        if detection['confidence'] > 0.6:
            return main_type, detection['category'], detection['subcategory']
        return main_type, 'Others', 'Unknown'

    async def create_zip(self, files: List[Tuple[str, bytes, str]], timestamp: str) -> Tuple[bytes, Dict]:
        """Crée un ZIP organisé et retourne les statistiques"""
        stats = {
            'total': 0,
            'total_size': 0,
            'types': {'Images': {'size': 0, 'count': 0}, 'Videos': {'size': 0, 'count': 0}},
            'categories': {}
        }
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            base_folder = f"media_collection_{timestamp}"
            
            for filename, content, (main_type, category, subcategory) in files:
                # Créer le chemin
                path = f"{base_folder}/{main_type}/{category}"
                if subcategory != "Unknown":
                    path += f"/{subcategory}"
                path += f"/{filename}"
                
                # Ajouter au ZIP
                zip_file.writestr(path, content)
                
                # Mettre à jour les statistiques
                file_size = len(content)
                stats['total'] += 1
                stats['total_size'] += file_size
                stats['types'][main_type]['count'] += 1
                stats['types'][main_type]['size'] += file_size
                
                # Mettre à jour les stats par catégorie
                if category not in stats['categories']:
                    stats['categories'][category] = {
                        'count': 0,
                        'size': 0,
                        'subcategories': {}
                    }
                stats['categories'][category]['count'] += 1
                stats['categories'][category]['size'] += file_size
                
                if subcategory != "Unknown":
                    if subcategory not in stats['categories'][category]['subcategories']:
                        stats['categories'][category]['subcategories'][subcategory] = {
                            'count': 0,
                            'size': 0
                        }
                    stats['categories'][category]['subcategories'][subcategory]['count'] += 1
                    stats['categories'][category]['subcategories'][subcategory]['size'] += file_size
        
        return zip_buffer.getvalue(), stats

    async def organize_and_upload(self, media_files: Dict[str, List[discord.Attachment]]) -> Tuple[Dict, str]:
        """Upload tous les fichiers dans un ZIP organisé"""
        try:
            # Analyser et télécharger les fichiers
            processed_files = []
            for media_type, files in media_files.items():
                for file in files:
                    print(f"Processing: {file.filename}")
                    file_data = await file.read()
                    classification = await self.analyze_and_sort_file(file_data, file.filename)
                    processed_files.append((file.filename, file_data, classification))
                    print(f"Classified {file.filename} as {classification}")

            # Créer le ZIP
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_data, stats = await self.create_zip(processed_files, timestamp)
            
            # Upload le ZIP
            zip_filename = f"media_collection_{timestamp}.zip"
            url = await self.upload_file(zip_data, zip_filename)
            
            return stats, url

        except Exception as e:
            print(f"Error in organize_and_upload: {e}")
            raise

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