import os
import torch
import sys
import importlib.util
from pathlib import Path

MODELS_CACHE_DIR = "cache/models"

def load_yolo_model():
    """Load YOLOv5 model with caching"""
    cache_path = Path(MODELS_CACHE_DIR) / "yolov5.pt"
    
    # Create cache directory if it doesn't exist
    os.makedirs(MODELS_CACHE_DIR, exist_ok=True)
    
    try:
        # Temporarily modify sys.path to avoid conflicts
        original_path = sys.path.copy()
        original_modules = sys.modules.copy()
        
        # Remove current directory from path to avoid importing local utils
        if '' in sys.path:
            sys.path.remove('')
        if '.' in sys.path:
            sys.path.remove('.')
        
        # Add a path to the beginning to prioritize YOLOv5's utils
        sys.path.insert(0, str(Path(torch.__file__).parent.parent))
            
        try:
            # Force reload torch.hub to avoid caching issues
            if 'torch.hub' in sys.modules:
                del sys.modules['torch.hub']
            
            if cache_path.exists():
                print("Loading YOLOv5 model from cache...")
                model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True, force_reload=False, trust_repo=True)
            else:
                print("Downloading YOLOv5 model...")
                model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True, trust_repo=True)
                # Save to cache
                torch.save(model.state_dict(), cache_path)
            return model
        finally:
            # Restore original path and modules
            sys.path = original_path
            # Only restore modules that were present before
            for module_name in list(sys.modules.keys()):
                if module_name not in original_modules:
                    del sys.modules[module_name]
    except Exception as e:
        print(f"Error loading YOLOv5 model: {str(e)}")
        import traceback
        traceback.print_exc()
        return None 