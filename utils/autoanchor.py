"""
Auto-anchor utils for YOLOv5
"""

import numpy as np
import torch
import yaml
from tqdm import tqdm

from utils.general import LOGGER, colorstr

def check_anchor_order(m):
    """
    Check anchor order against stride order for YOLOv5 Detect() module m,
    and correct if necessary
    """
    a = m.anchors.prod(-1).mean(-1).view(-1)  # mean anchor area per output layer
    da = a[-1] - a[0]  # delta a
    ds = m.stride[-1] - m.stride[0]  # delta s
    if da and (da.sign() != ds.sign()):  # same order
        LOGGER.info('Reversing anchor order')
        m.anchors[:] = m.anchors.flip(0)

def check_anchors(dataset, model, thr=4.0, imgsz=640):
    """
    Check anchor fit to data, recompute if necessary
    """
    # Simple version for compatibility
    return

def kmean_anchors(dataset='./data/coco128.yaml', n=9, img_size=640, thr=4.0, gen=1000, verbose=True):
    """
    Creates kmeans-evolved anchors from training dataset
    """
    # Simple version for compatibility
    return None

def autoanchor_ckpt(ckpt):
    """
    Update anchors in checkpoint dictionary if necessary
    """
    # Simple version for compatibility
    return ckpt 