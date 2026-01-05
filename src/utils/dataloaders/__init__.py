"""
Dataloaders module for YOLOv5 compatibility.
This is a minimal implementation to satisfy imports.
"""
from PIL import Image, ImageOps
import numpy as np
import cv2

def letterbox(im, new_shape=(640, 640), color=(114, 114, 114), auto=True, scaleFill=False, scaleup=True, stride=32):
    """
    Resize and pad image while meeting stride-multiple constraints
    Returns:
        im (numpy.ndarray): Resized and padded image
        ratio (tuple): Width and height ratios between new and old dimensions
        (dw, dh) (tuple): Padding dimensions
    """
    shape = im.shape[:2]  # current shape [height, width]
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)

    # Scale ratio (new / old)
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    if not scaleup:  # only scale down, do not scale up (for better val mAP)
        r = min(r, 1.0)

    # Compute padding
    ratio = r, r  # width, height ratios
    new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # wh padding
    if auto:  # minimum rectangle
        dw, dh = np.mod(dw, stride), np.mod(dh, stride)  # wh padding
    elif scaleFill:  # stretch
        dw, dh = 0.0, 0.0
        new_unpad = (new_shape[1], new_shape[0])
        ratio = new_shape[1] / shape[1], new_shape[0] / shape[0]  # width, height ratios

    dw /= 2  # divide padding into 2 sides
    dh /= 2

    if shape[::-1] != new_unpad:  # resize
        im = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    im = cv2.copyMakeBorder(im, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return im, ratio, (dw, dh)

def exif_transpose(image):
    """
    Transpose a PIL image accordingly if it has an EXIF Orientation tag.
    Inplace version of https://github.com/python-pillow/Pillow/blob/master/src/PIL/ImageOps.py exif_transpose()
    :param image: The image to transpose.
    :return: An image.
    """
    try:
        return ImageOps.exif_transpose(image)
    except Exception:
        return image

class LoadImages:
    """Load images for inference."""
    def __init__(self, *args, **kwargs):
        pass
    
    def __iter__(self):
        return self
    
    def __next__(self):
        raise StopIteration

class LoadStreams:
    """Load streams for inference."""
    def __init__(self, *args, **kwargs):
        pass
    
    def __iter__(self):
        return self
    
    def __next__(self):
        raise StopIteration

def create_dataloader(*args, **kwargs):
    """Create dataloader."""
    return None, None
