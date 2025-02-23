import aiohttp
from typing import Dict, List, Tuple
import discord

class AnonFilesUploader:
    def __init__(self):
        self.base_url = "https://api.anonfiles.com/upload"

    async def upload_file(self, file_data: bytes, filename: str) -> str:
        """Upload un fichier"""
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file', file_data, filename=filename)
                
                async with session.post(self.base_url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result["status"]:
                            return result["data"]["file"]["url"]["short"]
                    raise Exception(f"Upload failed: {await response.text()}")
        except Exception as e:
            print(f"Error uploading file: {e}")
            raise

    async def organize_and_upload(self, media_files: Dict[str, List[discord.Attachment]]) -> str:
        """Upload tous les fichiers"""
        try:
            # Upload chaque fichier
            uploaded_files = []
            for media_type, files in media_files.items():
                for file in files:
                    print(f"Processing file: {file.filename}")
                    file_data = await file.read()
                    url = await self.upload_file(file_data, file.filename)
                    uploaded_files.append(url)
                    print(f"Uploaded {file.filename}")

            # Retourner l'URL du dernier fichier (qui sera un ZIP si multiple)
            return uploaded_files[-1]

        except Exception as e:
            print(f"Error in organize_and_upload: {e}")
            raise 