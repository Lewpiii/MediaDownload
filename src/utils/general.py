"""
General utils for YOLOv5 compatibility
"""
import contextlib
import platform
import threading
import time
import math
import torch
import numpy as np
import logging
from pathlib import Path
import os
import sys
import subprocess
import pkg_resources as pkg
from IPython import get_ipython
import yaml
import urllib.parse
import glob

# Configure logging
LOGGER = logging.getLogger("yolov5")
LOGGER.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
LOGGER.addHandler(handler)

# Define ROOT
FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]  # YOLOv5 root directory
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH

class Profile(contextlib.ContextDecorator):
    """
    YOLOv5 Profile class.
    Usage: @Profile() decorator or 'with Profile():' context manager
    """
    def __init__(self, t=0.0):
        self.t = t
        self.cuda = torch.cuda.is_available()

    def __enter__(self):
        self.start = self.time()
        return self

    def __exit__(self, type, value, traceback):
        self.dt = self.time() - self.start  # delta-time
        self.t += self.dt  # accumulate dt

    def time(self):
        if self.cuda:
            torch.cuda.synchronize()
        return time.time()

def check_img_size(imgsz, s=32, floor=0):
    """Verify image size is a multiple of stride s in each dimension."""
    if isinstance(imgsz, int):  # integer i.e. img_size=640
        new_size = max(make_divisible(imgsz, int(s)), floor)
        return new_size if new_size == imgsz else LOGGER.warning(f'WARNING: --img-size {imgsz} must be multiple of max stride {s}, updating to {new_size}')
    else:  # list i.e. img_size=[640, 480]
        return [max(make_divisible(x, int(s)), floor) for x in imgsz]

def make_divisible(x, divisor):
    """Returns nearest x divisible by divisor."""
    if isinstance(divisor, torch.Tensor):
        divisor = int(divisor.max())  # to int
    return math.ceil(x / divisor) * divisor

def check_version(current='0.0.0', minimum='0.0.0', name='version', pinned=False, hard=False, verbose=False):
    """Return True if current version is greater than or equal to minimum version."""
    return True

def colorstr(*input):
    """Colors a string."""
    *args, string = input if len(input) > 1 else ('blue', 'bold', input[0])
    return string

def print_args(args=None, show_file=True):
    """Print function arguments (optional args dict)."""
    pass

def set_logging(name=None, verbose=True):
    """Sets up logging for the given name."""
    pass

def init_seeds(seed=0, deterministic=False):
    """Initialize random number generator (RNG) seeds."""
    pass

def get_latest_run(search_dir='.'):
    """Return path to most recent 'last.pt' in /runs (i.e. to --resume from)."""
    pass

def strip_optimizer(f='best.pt', s=''):
    """Strip optimizer from 'f' to finalize training, optionally save as 's'."""
    pass

def increment_path(path, exist_ok=False, sep='', mkdir=False):
    """Increment file or directory path."""
    return path

def scale_boxes(img1_shape, boxes, img0_shape, ratio_pad=None):
    """Rescale boxes (xyxy) from img1_shape to img0_shape."""
    return boxes

def non_max_suppression(prediction, conf_thres=0.25, iou_thres=0.45, classes=None, agnostic=False, multi_label=False,
                        labels=(), max_det=300):
    """Runs Non-Maximum Suppression (NMS) on inference results."""
    return prediction

def clip_boxes(boxes, shape):
    """Clip boxes (xyxy) to image shape (height, width)."""
    return boxes

def scale_coords(img1_shape, coords, img0_shape, ratio_pad=None):
    """Rescale coords (xyxy) from img1_shape to img0_shape."""
    return coords

def xyxy2xywh(x):
    """Convert nx4 boxes from [x1, y1, x2, y2] to [x, y, w, h] where xy1=top-left, xy2=bottom-right."""
    y = x.clone() if isinstance(x, torch.Tensor) else np.copy(x)
    y[:, 0] = (x[:, 0] + x[:, 2]) / 2  # x center
    y[:, 1] = (x[:, 1] + x[:, 3]) / 2  # y center
    y[:, 2] = x[:, 2] - x[:, 0]  # width
    y[:, 3] = x[:, 3] - x[:, 1]  # height
    return y

def xywh2xyxy(x):
    """Convert nx4 boxes from [x, y, w, h] to [x1, y1, x2, y2] where xy1=top-left, xy2=bottom-right."""
    y = x.clone() if isinstance(x, torch.Tensor) else np.copy(x)
    y[:, 0] = x[:, 0] - x[:, 2] / 2  # top left x
    y[:, 1] = x[:, 1] - x[:, 3] / 2  # top left y
    y[:, 2] = x[:, 0] + x[:, 2] / 2  # bottom right x
    y[:, 3] = x[:, 1] + x[:, 3] / 2  # bottom right y
    return y

def check_requirements(requirements=[], exclude=(), install=True, cmds=''):
    """
    Check if installed dependencies meet YOLOv5 requirements and attempt to auto-update if needed.
    Args:
        requirements (Union[Path, str, List[str]]): Requirements to check
        exclude (Tuple[str]): Packages to ignore
        install (bool): If True, attempt to auto-update packages
        cmds (str): Additional commands to run
    Returns:
        None
    """
    if isinstance(requirements, (str, Path)):
        requirements = [str(requirements)]
    elif isinstance(requirements, Path):
        requirements = [str(requirements)]
    else:
        requirements = [str(r) for r in requirements]

    try:
        # Si le premier requirement est un fichier requirements.txt
        if requirements and requirements[0].endswith('.txt'):
            LOGGER.info(f'Installing dependencies from: {requirements[0]}')
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements[0]])
            except Exception as e:
                LOGGER.warning(f'Error installing dependencies: {e}')
            return None

        # Sinon, installation normale des packages
        pkg_resources = pkg.working_set
        installed = {pkg.key for pkg in pkg_resources}
        
        requirements = [x.strip() for x in requirements]
        missing = []
        
        for r in requirements:
            try:
                pkg.require(r)
            except Exception:
                missing.append(r)
        
        if install and missing:
            LOGGER.info(f'Installing dependencies: {", ".join(missing)}')
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])
            except Exception as e:
                LOGGER.warning(f'Error installing dependencies: {e}')
                
    except Exception as e:
        LOGGER.warning(f'Error checking requirements: {e}')
    
    return None

def check_suffix(file='yolov5s.pt', suffix=('.pt',), msg=''):
    """Check file suffix against accepted suffixes."""
    if file and suffix:
        if isinstance(suffix, str):
            suffix = [suffix]
        for f in file if isinstance(file, (list, tuple)) else [file]:
            s = Path(f).suffix.lower()  # file suffix
            if len(s):
                assert s in suffix, f"{msg}{f} acceptable suffix is {suffix}"
    return file 

def is_jupyter():
    """Check if the current environment is a Jupyter notebook."""
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':  # Jupyter notebook or qtconsole
            return True
        elif shell == 'TerminalInteractiveShell':  # Terminal running IPython
            return False
        else:
            return False
    except:
        return False 

def yaml_load(file='data.yaml', append_filename=False):
    """
    Load YAML data from a file.
    Args:
        file (str, optional): File name. Defaults to 'data.yaml'.
        append_filename (bool): Add filename to dict as 'filename' key
    Returns:
        dict: YAML contents
    """
    with open(file, errors='ignore', encoding='utf-8') as f:
        s = f.read()  # string
        if not s.isprintable():  # remove special characters
            s = ''.join(c if c.isprintable() else ' ' for c in s)
        try:
            data = yaml.safe_load(s)  # dict
            if append_filename:
                data['filename'] = str(file)
            return data
        except yaml.YAMLError as e:
            LOGGER.error(f'YAML load failure: {file} {e}')
            return None 

def check_yaml(file, suffix=('.yaml', '.yml')):
    """
    Search/download YAML file (if necessary) and return path, checking suffix.
    """
    return check_suffix(file, suffix)  # Vérifie le suffixe

def check_file(file, suffix=''):
    """
    Search/download file (if necessary) and return path.
    """
    check_suffix(file, suffix)  # Vérifie le suffixe
    file = str(file)  # convertit en string
    if Path(file).is_file() or not file:  # existe
        return file
    elif file.startswith(('http:/', 'https:/')):  # télécharge
        url = file  # warning: Pathlib turns :// -> :/
        file = Path(urllib.parse.unquote(file).split('?')[0]).name  # basename
        if Path(file).is_file():
            LOGGER.info(f'Found {file} locally')
        else:
            LOGGER.info(f'Downloading {url} to {file}...')
            torch.hub.download_url_to_file(url, file)
        return file
    else:  # recherche
        files = []
        for d in ('data', 'models', 'utils'):  # recherche dans les dossiers
            files.extend(glob.glob(str(ROOT / d / '**' / file), recursive=True))
        if not files:
            raise FileNotFoundError(f"File '{file}' not found")
        elif len(files) == 1:
            return files[0]  # retourne le fichier si unique
        else:
            raise FileNotFoundError(f"Multiple files match '{file}', specify exact path: {files}") 

def intersect_dicts(da, db, exclude=()):
    """
    Returns dictionary of intersecting keys with matching shapes.
    Args:
        da (dict): first dictionary
        db (dict): second dictionary
        exclude (tuple): keys to exclude
    Returns:
        dict: intersecting keys with matching shapes
    """
    return {k: v for k, v in da.items() if k in db 
            and not any(x in k for x in exclude) 
            and v.shape == db[k].shape} 