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
                data = aiohttp.FormData()
                data.add_field('file', file_data, filename=filename)
                if folder_id:
                    data.add_field('folderId', folder_id)
                if self.guest_token:
                    data.add_field('token', self.guest_token)
                
                upload_url = f"https://{server}.gofile.io/contents/uploadfile"
                print(f"Uploading to: {upload_url}")
                
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
        """Upload tous les fichiers dans le même dossier"""
        try:
            # 1. Obtenir le serveur
            server = await self.get_server()
            print(f"Using server: {server}")

            # 2. Upload les fichiers
            folder_id = None
            download_url = None
            self.guest_token = None

            for media_type, files in media_files.items():
                for file in files:
                    print(f"Processing file: {file.filename}")
                    file_data = await file.read()
                    
                    # Pour le premier fichier, on récupère le parentFolderCode
                    if not folder_id:
                        folder_id, download_url = await self.upload_file(file_data, file.filename, server)
                    else:
                        # Pour les fichiers suivants, on utilise le même parentFolderCode
                        _, _ = await self.upload_file(file_data, file.filename, server, folder_id)
                    
                    print(f"Uploaded {file.filename} to folder {folder_id}")

            if not download_url:
                raise Exception("No files were uploaded successfully")
            return download_url

        except Exception as e:
            print(f"Error in organize_and_upload: {e}")
            raise 