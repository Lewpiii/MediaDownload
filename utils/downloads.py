"""
Download utils for YOLOv5
"""

import os
import platform
import subprocess
import urllib
from pathlib import Path

import requests
import torch

from utils.general import LOGGER, check_requirements, colorstr

def attempt_download(file, repo='ultralytics/yolov5', release='v7.0'):
    """
    Attempts to download a file from GitHub release assets or via direct URL.
    """
    def github_assets(repository, version='latest'):
        # Return GitHub repo tag and assets (i.e. ['yolov5s.pt', 'yolov5m.pt', ...])
        if version != 'latest':
            version = f'tags/{version}'  # i.e. tags/v6.2
        response = requests.get(f'https://api.github.com/repos/{repository}/releases/{version}').json()
        return response['tag_name'], [x['name'] for x in response['assets']]

    file = str(file)
    if Path(file).is_file():
        LOGGER.info(f"Found {file} locally")
        return file
    elif file.startswith(('http:/', 'https:/')):
        url = file  # download url
        name = Path(urllib.parse.unquote(Path(url).name)).name  # decode '%2F' to '/' etc.
        download(url, name)
        return name

    # GitHub assets
    assets = [f'yolov5{size}{suffix}.pt' for size in 'nsmlx' for suffix in ('', '6', '-cls', '-seg')]  # default assets
    try:
        tag, assets = github_assets(repo, release)
    except Exception:
        try:
            tag, assets = github_assets(repo)  # latest release
        except Exception:
            try:
                tag = subprocess.check_output(['git', 'tag']).decode().split()[-1]
            except Exception:
                tag = release

    file = str(file)
    if Path(file).is_file():
        LOGGER.info(f'Found {file} locally')
    else:
        LOGGER.info(f'Downloading {file} from GitHub...')
        url = f'https://github.com/{repo}/releases/download/{tag}/{file}'
        download(url, file)
    return file

def download(url, file=''):
    """
    Downloads files from a URL.
    """
    file = Path(file)
    if not file.exists():
        LOGGER.info(f'Downloading {url} to {file}...')
        torch.hub.download_url_to_file(url, str(file))
    if file.exists():
        LOGGER.info(f"Downloaded {file.name} successfully")
        return file
    else:
        LOGGER.info(f"Failed to download {file.name}")
        return None

def safe_download(file, url, min_bytes=1E0, error_msg=''):
    """
    Attempts to download file from url or url2, checks and removes incomplete downloads < min_bytes
    """
    file = Path(file)
    assert_msg = f"Downloaded file '{file}' does not exist or size is < min_bytes={min_bytes}"
    try:  # url1
        download(url, str(file))
        assert file.exists() and file.stat().st_size > min_bytes, assert_msg  # check
    except Exception as e:  # remove partial downloads
        LOGGER.warning(f'ERROR: {e}')
        if file.exists():
            file.unlink()  # remove partial downloads
        LOGGER.info(f'Re-attempting {url} to {file}...')
        os.system(f"curl -# -L '{url}' -o '{file}' --retry 3 -C -")  # curl download, retry and resume on fail
    finally:
        if not file.exists() or file.stat().st_size < min_bytes:  # check
            if file.exists():
                file.unlink()  # remove partial downloads
            LOGGER.info(f'ERROR: {error_msg or assert_msg}')
            return False
        return True 