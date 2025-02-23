import aiohttp
from typing import Dict, List, Tuple
import discord
import json

class PixelDrainUploader:
    def __init__(self):
        self.base_url = "https://pixeldrain.com/api"

    async def upload_file(self, file_data: bytes, filename: str) -> str:
        """Upload un fichier"""
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file', file_data, filename=filename)
                
                print(f"Uploading file: {filename}")
                upload_url = f"{self.base_url}/file"  # Endpoint public
                
                async with session.post(upload_url, data=data) as response:
                    print(f"Upload response status: {response.status}")
                    if response.status in [200, 201]:
                        result = await response.json()
                        print(f"Upload response: {result}")
                        file_id = result.get('id')
                        if file_id:
                            return f"https://pixeldrain.com/u/{file_id}"
                    response_text = await response.text()
                    print(f"Error response: {response_text}")
                    raise Exception(f"Upload failed: {response_text}")
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

            # Si plusieurs fichiers, créer une liste de liens
            if len(uploaded_files) > 1:
                return "\n".join(uploaded_files)
            
            # Si un seul fichier, retourner son URL
            return uploaded_files[0]

        except Exception as e:
            print(f"Error in organize_and_upload: {e}")
            raise 