import aiohttp
import time
import os
from typing import Dict, List, Any
import discord

class GoFileUploader:
    def __init__(self, token: str = None):
        self.token = token  # Optionnel maintenant
        self.base_url = "https://api.gofile.io"
        self.server = None

    async def get_server(self) -> str:
        """Obtient le meilleur serveur pour l'upload"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/getServer") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["data"]["server"]
                    raise Exception(f"Failed to get server: {response.status}")
        except Exception as e:
            print(f"Error getting server: {e}")
            raise

    async def upload_file(self, file_data: bytes, filename: str, server: str) -> str:
        """Upload un fichier"""
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file', file_data, filename=filename)
                
                async with session.post(f"https://{server}.gofile.io/uploadFile", data=data) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data["status"] == "ok":
                            return data["data"]["downloadPage"]
                    response_text = await response.text()
                    raise Exception(f"File upload failed: {response_text}")
        except Exception as e:
            print(f"Error uploading file: {e}")
            raise

    async def create_folder(self, folder_name: str, parent_id: str = None) -> Dict[str, Any]:
        """Crée un nouveau dossier"""
        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "token": self.token,
                    "folderName": folder_name,
                    "parentFolderId": parent_id
                }
                async with session.put(f"{self.base_url}/createFolder", json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result["status"] == "ok":
                            return result["data"]
                    raise Exception(f"Folder creation failed: {await response.text()}")
        except Exception as e:
            print(f"Error creating folder: {e}")
            raise

    @staticmethod
    def detect_category(filename: str) -> str:
        """Détecte la catégorie d'un fichier"""
        filename_lower = filename.lower()
        
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
        
        for keyword, category in CATEGORIES.items():
            if keyword in filename_lower:
                return category
        
        return "Others"

    async def organize_and_upload(self, media_files: Dict[str, List[discord.Attachment]]) -> str:
        """Upload tous les fichiers"""
        try:
            # 1. Obtenir le serveur
            server = await self.get_server()
            print(f"Using server: {server}")

            # 2. Upload les fichiers
            upload_urls = []
            for media_type, files in media_files.items():
                for file in files:
                    file_data = await file.read()
                    download_url = await self.upload_file(file_data, file.filename, server)
                    upload_urls.append(download_url)
                    print(f"Uploaded {file.filename}: {download_url}")

            # 3. Retourner l'URL du premier fichier
            return upload_urls[0] if upload_urls else ""

        except Exception as e:
            print(f"Error in organize_and_upload: {e}")
            raise 