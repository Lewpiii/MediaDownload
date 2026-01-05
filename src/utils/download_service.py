import os
import aiohttp
import asyncio
import logging
import zipfile
import time
import psutil
from datetime import timedelta
from ..config import DOWNLOAD_CONFIG, MAX_SINGLE_FILE_SIZE, RESOURCE_LIMITS

logger = logging.getLogger('bot.download_service')

class ResourceMonitor:
    def __init__(self):
        self.memory_threshold = RESOURCE_LIMITS['memory_threshold']
        self.disk_threshold = RESOURCE_LIMITS['disk_threshold']
        self.start_time = None
        self.processed_items = 0
        self.total_items = 0

    def start_monitoring(self, total_items):
        self.start_time = time.time()
        self.total_items = total_items
        self.processed_items = 0

    def should_pause(self) -> tuple[bool, str]:
        """Check if we should pause processing"""
        try:
            mem = self.get_memory_usage()
            disk = self.get_disk_usage()
            
            if mem['percent'] > self.memory_threshold:
                return True, f"Memory usage too high ({mem['percent']:.1f}%)"
            if disk['percent'] > self.disk_threshold:
                return True, f"Disk usage too high ({disk['percent']}%)"
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
        return False, ""

    @staticmethod
    def get_memory_usage():
        process = psutil.Process()
        mem_info = process.memory_info()
        return {
            'rss': mem_info.rss / 1024 / 1024,
            'percent': process.memory_percent()
        }
    
    @staticmethod
    def get_disk_usage(path: str = None):
        if path is None:
            path = DOWNLOAD_CONFIG['temp_dir']
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
        disk = psutil.disk_usage(path)
        return {
            'free': disk.free / 1024 / 1024 / 1024,
            'percent': disk.percent
        }

    @staticmethod
    def log_resources(logger_instance=logger):
        try:
            mem = ResourceMonitor.get_memory_usage()
            disk = ResourceMonitor.get_disk_usage()
            logger_instance.info(f"Memory: {mem['rss']:.1f}MB ({mem['percent']:.1f}%) | Disk: {disk['percent']}% used")
        except Exception:
            pass

class DownloadService:
    @staticmethod
    async def download_file_in_chunks(url: str, file_path: str, chunk_size: int = None, max_retries: int = 3) -> bool:
        """Download a file in chunks with timeout handling and retry logic"""
        if chunk_size is None:
            chunk_size = DOWNLOAD_CONFIG['chunk_size']
            
        timeout = aiohttp.ClientTimeout(
            total=DOWNLOAD_CONFIG['timeout_total'],
            connect=DOWNLOAD_CONFIG['timeout_connect'],
            sock_read=DOWNLOAD_CONFIG['timeout_read']
        )
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            total_size = int(response.headers.get('content-length', 0))
                            
                            if total_size > MAX_SINGLE_FILE_SIZE:
                                logger.warning(f"File too large: {total_size} bytes")
                                return False
                                
                            os.makedirs(os.path.dirname(file_path), exist_ok=True)
                            
                            with open(file_path, 'wb') as f:
                                async for chunk in response.content.iter_chunked(chunk_size):
                                    f.write(chunk)
                            
                            return True
                        else:
                            logger.error(f"HTTP {response.status} for {url}")
                            
            except (aiohttp.ClientTimeout, asyncio.TimeoutError):
                logger.warning(f"Timeout attempt {attempt+1}/{max_retries} for {url}")
            except Exception as e:
                logger.error(f"Error attempt {attempt+1}/{max_retries} for {url}: {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                
        return False

    @staticmethod
    async def create_zip_in_chunks(files: list, zip_path: str) -> None:
        """Create ZIP file streaming from disk"""
        try:
            compress_level = DOWNLOAD_CONFIG['compress_level']
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=compress_level) as zf:
                for file_path in files:
                    if os.path.exists(file_path):
                        zf.write(file_path, os.path.basename(file_path))
                        if DOWNLOAD_CONFIG['cleanup_after_zip']:
                            try:
                                os.remove(file_path)
                            except OSError:
                                pass
        except Exception as e:
            logger.error(f"Error creating ZIP: {e}")
            raise
