import aiohttp
import time
import os
from typing import Dict, List, Any
import discord

class GoFileUploader:
    def __init__(self, token: str = None):
        self.token = token
        self.base_url = "https://api.gofile.io"
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.guest_token = None

    async def get_server(self) -> str:
        """Obtient un serveur pour l'upload"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/servers") as response:
                    print(f"Server response status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"Server response data: {data}")
                        if data.get("status") == "ok":
                            # On prend le premier serveur de la liste 'servers'
                            server = data["data"]["servers"][0]["name"]
                            print(f"Selected server: {server}")
                            return server
                        raise Exception(f"Invalid server response: {data}")
                    response_text = await response.text()
                    raise Exception(f"Failed to get server: {response_text}")
        except Exception as e:
            print(f"Error getting server: {e}")
            raise

    async def upload_file(self, file_data: bytes, filename: str, server: str, folder_id: str = None) -> tuple:
        """Upload un fichier"""
        try:
            async with aiohttp.ClientSession() as session:
                # Création du FormData
                data = aiohttp.FormData()
                data.add_field('file', file_data, filename=filename)
                
                # Ajout des paramètres optionnels
                if folder_id:
                    data.add_field('parentFolder', folder_id)
                if self.guest_token:
                    data.add_field('token', self.guest_token)
                
                # URL correcte pour l'upload
                upload_url = f"https://{server}.gofile.io/uploadFile"
                
                headers = {
                    'Accept': 'application/json'
                }
                
                print(f"Uploading to: {upload_url}")
                print(f"Using folder_id: {folder_id}")
                print(f"Using guest_token: {self.guest_token}")
                
                async with session.post(upload_url, data=data, headers=headers) as response:
                    print(f"Upload response status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"Upload response data: {data}")
                        if data["status"] == "ok":
                            # Sauvegarder le guest token du premier upload
                            if not self.guest_token:
                                self.guest_token = data["data"]["token"]
                                print(f"Saved guest token: {self.guest_token}")
                            
                            # Pour le premier fichier
                            if not folder_id:
                                return data["data"]["parentFolder"], data["data"]["downloadPage"]
                            return None, data["data"]["downloadPage"]
                    response_text = await response.text()
                    raise Exception(f"File upload failed: {response_text}")
        except Exception as e:
            print(f"Error uploading file: {e}")
            raise

    async def create_folder(self, token: str, folder_name: str) -> Dict[str, Any]:
        """Crée un nouveau dossier"""
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.gofile.io/createFolder"
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                data = {
                    "parentFolderId": None,
                    "folderName": folder_name
                }
                
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result["status"] == "ok":
                            return result["data"]
                    raise Exception(f"Failed to create folder: {await response.text()}")
        except Exception as e:
            print(f"Error creating folder: {e}")
            return None

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
        """Upload tous les fichiers dans le même dossier"""
        try:
            # 1. Obtenir le serveur
            server = await self.get_server()
            print(f"Using server: {server}")

            # 2. Upload le premier fichier pour obtenir le folder_id
            first_file = next(iter(media_files.values()))[0]
            file_data = await first_file.read()
            folder_id, download_url = await self.upload_file(file_data, first_file.filename, server)
            print(f"First file uploaded, got folder_id: {folder_id}")

            # 3. Upload tous les autres fichiers dans le même dossier
            for media_type, files in media_files.items():
                for file in files:
                    if file != first_file:  # Skip the first file as it's already uploaded
                        print(f"Processing file: {file.filename}")
                        file_data = await file.read()
                        _, _ = await self.upload_file(file_data, file.filename, server, folder_id)
                        print(f"Uploaded {file.filename} to folder {folder_id}")

            # 4. Retourner l'URL du dossier
            return f"https://gofile.io/d/{folder_id}"

        except Exception as e:
            print(f"Error in organize_and_upload: {e}")
            raise 