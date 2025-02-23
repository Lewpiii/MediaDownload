import aiohttp
import time
import os
from typing import Dict, List, Any

class GoFileUploader:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.gofile.io"
        self.server = None

    async def get_best_server(self) -> str:
        """Obtient le meilleur serveur disponible"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/getServer") as response:
                    if response.status == 200:
                        data = await response.json()
                        if data["status"] == "ok":
                            self.server = data["data"]["server"]
                            return self.server
            raise Exception("Couldn't get server")
        except Exception as e:
            print(f"Error getting server: {e}")
            raise

    async def upload_file(self, file_path: str, folder_id: str = None) -> Dict[str, Any]:
        """Upload un fichier sur Gofile"""
        if not self.server:
            await self.get_best_server()
            
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file', open(file_path, 'rb'))
                if folder_id:
                    data.add_field('folderId', folder_id)
                data.add_field('token', self.token)
                
                url = f"https://{self.server}.gofile.io/uploadFile"
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result["status"] == "ok":
                            return result["data"]
                    raise Exception(f"Upload failed: {await response.text()}")
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

    async def organize_and_upload(self, files_dict: Dict[str, List[Any]]) -> str:
        """Organise et upload les fichiers selon leur catégorie"""
        try:
            # Créer le dossier principal
            main_folder = await self.create_folder(f"Discord_Download_{int(time.time())}")
            main_folder_id = main_folder["id"]
            
            # Pour chaque type (Images/Videos)
            for media_type, files in files_dict.items():
                if not files:
                    continue
                    
                # Créer le dossier pour le type de média
                type_folder = await self.create_folder(media_type, main_folder_id)
                
                # Organiser les fichiers par catégorie
                categorized_files = {}
                for file in files:
                    category = self.detect_category(file.filename)
                    if category not in categorized_files:
                        categorized_files[category] = []
                    categorized_files[category].append(file)
                
                # Créer les dossiers de catégories et uploader les fichiers
                for category, cat_files in categorized_files.items():
                    if category != "Others":
                        cat_folder = await self.create_folder(category, type_folder["id"])
                        folder_id = cat_folder["id"]
                    else:
                        folder_id = type_folder["id"]
                    
                    for file in cat_files:
                        await self.upload_file(file.filename, folder_id)
            
            return main_folder["downloadPage"]
            
        except Exception as e:
            print(f"Error in organize_and_upload: {e}")
            raise 