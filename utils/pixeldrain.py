import aiohttp
from typing import Dict, List, Tuple
import discord

class PixelDrainUploader:
    def __init__(self):
        self.base_url = "https://pixeldrain.com/api"

    async def upload_file(self, file_data: bytes, filename: str) -> str:
        """Upload un fichier"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Content-Type': 'application/octet-stream'
                }
                
                print(f"Uploading file: {filename}")
                async with session.put(f"{self.base_url}/file/{filename}", data=file_data, headers=headers) as response:
                    print(f"Upload response status: {response.status}")
                    if response.status in [200, 201]:
                        result = await response.json()
                        print(f"Upload response: {result}")
                        return f"https://pixeldrain.com/u/{result['id']}"
                    response_text = await response.text()
                    print(f"Error response: {response_text}")
                    raise Exception(f"Upload failed: {response_text}")
        except Exception as e:
            print(f"Error uploading file: {e}")
            raise

    async def organize_and_upload(self, media_files: Dict[str, List[discord.Attachment]]) -> str:
        """Upload tous les fichiers et crée une liste"""
        try:
            # Upload chaque fichier
            file_ids = []
            for media_type, files in media_files.items():
                for file in files:
                    print(f"Processing file: {file.filename}")
                    file_data = await file.read()
                    url = await self.upload_file(file_data, file.filename)
                    file_ids.append(url)
                    print(f"Uploaded {file.filename}")

            # Si un seul fichier, retourner son URL
            if len(file_ids) == 1:
                return file_ids[0]
            
            # Si plusieurs fichiers, créer une liste
            list_description = "Media files"
            list_data = {
                "title": "Media Collection",
                "description": list_description,
                "files": [url.split('/')[-1] for url in file_ids]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/list", json=list_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return f"https://pixeldrain.com/l/{result['id']}"
                    raise Exception(f"List creation failed: {await response.text()}")

        except Exception as e:
            print(f"Error in organize_and_upload: {e}")
            raise 