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
                    data.add_field('parentFolderCode', folder_id)  # Utiliser parentFolderCode au lieu de parentFolder
                if self.guest_token:
                    data.add_field('token', self.guest_token)
                
                upload_url = f"https://{server}.gofile.io/contents/uploadfile"
                print(f"Uploading to: {upload_url}")
                print(f"Using folder_id: {folder_id}")
                print(f"Using guest_token: {self.guest_token}")
                
                async with session.post(upload_url, data=data) as response:
                    print(f"Upload response status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"Upload response data: {data}")
                        if data["status"] == "ok":
                            # Sauvegarder le guest token du premier upload
                            if not self.guest_token:
                                self.guest_token = data["data"]["guestToken"]
                                print(f"Saved guest token: {self.guest_token}")
                            # Si c'est le premier fichier, on retourne le parentFolderCode et l'URL
                            if not folder_id:
                                return data["data"]["parentFolderCode"], data["data"]["downloadPage"]
                            return None, data["data"]["downloadPage"]
                    response_text = await response.text()
                    raise Exception(f"File upload failed: {response_text}")
        except Exception as e:
            print(f"Error uploading file: {e}")
            raise

    async def create_folder(self, folder_name: str) -> Dict[str, Any]:
        """Crée un nouveau dossier"""
        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "token": self.guest_token,
                    "folderName": folder_name,
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
        """Upload tous les fichiers dans le même dossier"""
        try:
            # 1. Obtenir le serveur
            server = await self.get_server()
            print(f"Using server: {server}")

            # 2. Upload le premier fichier pour obtenir le guest token
            first_file = next(iter(media_files.values()))[0]
            file_data = await first_file.read()
            folder_id, download_url = await self.upload_file(file_data, first_file.filename, server)
            print(f"First file uploaded, got folder_id: {folder_id}")

            # 3. Créer un nouveau dossier avec le guest token
            folder_name = "media_collection"
            folder_info = await self.create_folder(folder_name)
            new_folder_id = folder_info["id"]
            print(f"Created new folder with ID: {new_folder_id}")

            # 4. Upload tous les fichiers dans le nouveau dossier
            for media_type, files in media_files.items():
                for file in files:
                    if file != first_file:  # Skip the first file as it's already uploaded
                        print(f"Processing file: {file.filename}")
                        file_data = await file.read()
                        _, _ = await self.upload_file(file_data, file.filename, server, new_folder_id)
                        print(f"Uploaded {file.filename} to folder {new_folder_id}")

            return f"https://gofile.io/d/{new_folder_id}"

        except Exception as e:
            print(f"Error in organize_and_upload: {e}")
            raise 