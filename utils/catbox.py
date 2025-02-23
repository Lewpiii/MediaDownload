import aiohttp
from typing import Dict, List, Tuple
import discord
import zipfile
import io
import os
import tempfile
from datetime import datetime

class CatboxUploader:
    def __init__(self):
        self.upload_url = "https://catbox.moe/user/api.php"

    async def download_file(self, url: str) -> bytes:
        """Télécharge un fichier depuis une URL"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.read()

    async def create_zip(self, files: List[Tuple[str, bytes]]) -> bytes:
        """Crée un fichier ZIP en mémoire"""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, content in files:
                zip_file.writestr(filename, content)
        return zip_buffer.getvalue()

    async def upload_file(self, file_data: bytes, filename: str) -> str:
        """Upload un fichier"""
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('reqtype', 'fileupload')
                data.add_field('userhash', '')
                data.add_field('fileToUpload', file_data, filename=filename)
                
                print(f"Uploading file: {filename}")
                
                async with session.post(self.upload_url, data=data) as response:
                    print(f"Upload response status: {response.status}")
                    if response.status == 200:
                        url = await response.text()
                        print(f"Upload response: {url}")
                        return url
                    response_text = await response.text()
                    print(f"Error response: {response_text}")
                    raise Exception(f"Upload failed: {response_text}")
        except Exception as e:
            print(f"Error uploading file: {e}")
            raise

    async def organize_and_upload(self, media_files: Dict[str, List[discord.Attachment]]) -> str:
        """Upload tous les fichiers dans un ZIP"""
        try:
            # Télécharger tous les fichiers
            files_to_zip = []
            for media_type, files in media_files.items():
                for file in files:
                    print(f"Processing file: {file.filename}")
                    file_data = await file.read()
                    files_to_zip.append((file.filename, file_data))
                    print(f"Downloaded {file.filename}")

            # Créer le ZIP
            print("Creating ZIP file...")
            zip_data = await self.create_zip(files_to_zip)
            
            # Upload le ZIP
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"media_collection_{timestamp}.zip"
            url = await self.upload_file(zip_data, zip_filename)
            
            # Retourner les statistiques et l'URL
            stats = {
                'total': len(files_to_zip),
                'types': {media_type: len(files) for media_type, files in media_files.items()}
            }
            
            return stats, url

        except Exception as e:
            print(f"Error in organize_and_upload: {e}")
            raise 