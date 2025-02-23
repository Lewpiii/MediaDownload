import aiohttp
from typing import Dict, List, Tuple
import discord

class CatboxUploader:
    def __init__(self):
        self.upload_url = "https://catbox.moe/user/api.php"

    async def upload_file(self, file_data: bytes, filename: str) -> str:
        """Upload un fichier"""
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('reqtype', 'fileupload')
                data.add_field('userhash', '')  # Pas besoin de hash pour upload anonyme
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