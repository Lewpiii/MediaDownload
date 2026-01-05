import torch
from PIL import Image
import cv2
import numpy as np
from pathlib import Path
import io
import os
import time

class MediaDetector:
    _instance = None
    _models_loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MediaDetector, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not MediaDetector._models_loaded:
            self.load_models()
            MediaDetector._models_loaded = True

    def load_models(self):
        """Charge les modèles avec gestion du rate limit"""
        try:
            print("Loading AI models...")
            
            # Définir un dossier de cache permanent
            self.cache_dir = Path("./model_cache")
            self.cache_dir.mkdir(exist_ok=True)
            
            # Charger depuis le cache si possible
            if (self.cache_dir / "yolov5s.pt").exists():
                print("Loading YOLOv5 from cache...")
                self.yolo_model = torch.hub.load('ultralytics/yolov5', 'yolov5s', trust_repo=True)
            else:
                print("Downloading YOLOv5 model...")
                torch.hub.set_dir(str(self.cache_dir))
                self.yolo_model = torch.hub.load('ultralytics/yolov5', 'yolov5s', trust_repo=True)

            # Attendre un peu entre les téléchargements
            time.sleep(2)
            
            # Charger ResNet avec cache local
            if not (self.cache_dir / "resnet18.pth").exists():
                print("Downloading ResNet model...")
                self.resnet_model = torch.hub.load('pytorch/vision:v0.10.0', 'resnet18', pretrained=True)
                torch.save(self.resnet_model.state_dict(), self.cache_dir / "resnet18.pth")
            else:
                print("Loading ResNet from cache...")
                self.resnet_model = torch.hub.load('pytorch/vision:v0.10.0', 'resnet18', pretrained=False)
                self.resnet_model.load_state_dict(torch.load(self.cache_dir / "resnet18.pth"))

            self.confidence_threshold = 0.6
            print("AI models loaded successfully!")

        except Exception as e:
            print(f"Error loading models: {e}")
            # Fallback à une version simplifiée si les modèles ne peuvent pas être chargés
            self.yolo_model = None
            self.resnet_model = None
            self.confidence_threshold = 0.6

    async def analyze_media(self, file_data: bytes, filename: str) -> dict:
        """Analyse un fichier média avec gestion des erreurs"""
        try:
            # Si les modèles n'ont pas pu être chargés, utiliser l'analyse basique
            if self.yolo_model is None or self.resnet_model is None:
                return self.basic_analysis(filename)

            # Analyse normale avec les modèles
            image = Image.open(io.BytesIO(file_data))
            yolo_results = self.yolo_model(image)
            resnet_results = self.analyze_with_resnet(image)
            return self.combine_results(yolo_results, resnet_results, filename)

        except Exception as e:
            print(f"Error in analyze_media: {e}")
            return self.basic_analysis(filename)

    def basic_analysis(self, filename: str) -> dict:
        """Analyse basique basée sur le nom de fichier"""
        filename_lower = filename.lower()
        
        # Détection basique des jeux
        if 'valorant' in filename_lower:
            return {"confidence": 0.8, "category": "Games", "subcategory": "Valorant"}
        elif 'minecraft' in filename_lower:
            return {"confidence": 0.8, "category": "Games", "subcategory": "Minecraft"}
        elif 'lol' in filename_lower or 'league' in filename_lower:
            return {"confidence": 0.8, "category": "Games", "subcategory": "League of Legends"}
        elif 'fortnite' in filename_lower:
            return {"confidence": 0.8, "category": "Games", "subcategory": "Fortnite"}
        
        # Détection basique des applications
        elif 'discord' in filename_lower:
            return {"confidence": 0.8, "category": "Apps", "subcategory": "Discord"}
        elif 'screenshot' in filename_lower:
            return {"confidence": 0.7, "category": "Screenshots", "subcategory": "System"}
        
        return {"confidence": 0.5, "category": "Others", "subcategory": "Unknown"}

    def analyze_with_resnet(self, image):
        """Analyse avec ResNet"""
        if self.resnet_model is None:
            return None
        # ... reste du code ResNet ...
        return None

    def combine_results(self, yolo_results, resnet_results, filename: str) -> dict:
        """Combine les résultats ou utilise l'analyse basique si nécessaire"""
        if yolo_results is None or resnet_results is None:
            return self.basic_analysis(filename)
        # ... reste du code de combinaison ...
        return self.basic_analysis(filename)  # Temporairement, utiliser l'analyse basique 