import os
import torch
from pathlib import Path

MODELS_CACHE_DIR = "cache/models"

def load_yolo_model():
    """Load YOLOv5 model with caching"""
    cache_path = Path(MODELS_CACHE_DIR) / "yolov5.pt"
    
    # Create cache directory if it doesn't exist
    os.makedirs(MODELS_CACHE_DIR, exist_ok=True)
    
    try:
        if cache_path.exists():
            print("Loading YOLOv5 model from cache...")
            model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True, force_reload=False)
        else:
            print("Downloading YOLOv5 model...")
            model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
            # Save to cache
            torch.save(model.state_dict(), cache_path)
        return model
    except Exception as e:
        print(f"Error loading YOLOv5 model: {str(e)}")
        return None 