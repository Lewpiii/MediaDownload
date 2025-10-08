"""
Performance optimization utilities for the Discord bot
"""
import asyncio
import psutil
import os
import time
from typing import Dict, List, Optional
import logging
from pathlib import Path

logger = logging.getLogger('bot.performance')

class PerformanceOptimizer:
    """Optimizes bot performance and resource usage"""
    
    def __init__(self):
        self.download_semaphore = asyncio.Semaphore(3)  # Max 3 concurrent downloads
        self.processing_queue = asyncio.Queue(maxsize=10)
        self.cache_dir = Path("./cache")
        self.cache_dir.mkdir(exist_ok=True)
        
    async def optimize_system(self):
        """Apply system-level optimizations"""
        try:
            # Set process priority to high
            if hasattr(os, 'nice'):
                os.nice(-5)  # Higher priority
            
            # Optimize Python garbage collection
            import gc
            gc.set_threshold(700, 10, 10)
            
            logger.info("System optimizations applied")
            
        except Exception as e:
            logger.warning(f"Could not apply system optimizations: {e}")
    
    def get_system_info(self) -> Dict:
        """Get comprehensive system information"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_total': memory.total,
                'memory_available': memory.available,
                'memory_percent': memory.percent,
                'disk_total': disk.total,
                'disk_free': disk.free,
                'disk_percent': disk.percent,
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {}
    
    async def cleanup_temp_files(self, temp_dir: str = "/tmp/discord_downloads"):
        """Clean up temporary files older than 1 hour"""
        try:
            temp_path = Path(temp_dir)
            if not temp_path.exists():
                return
                
            current_time = time.time()
            cleaned_count = 0
            
            for file_path in temp_path.iterdir():
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > 3600:  # 1 hour
                        try:
                            file_path.unlink()
                            cleaned_count += 1
                        except OSError:
                            pass
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} temporary files")
                
        except Exception as e:
            logger.error(f"Error cleaning temp files: {e}")
    
    async def monitor_resources(self, threshold_memory: float = 85.0, threshold_disk: float = 90.0):
        """Monitor system resources and return status"""
        try:
            system_info = self.get_system_info()
            
            if not system_info:
                return False, "Could not get system info"
            
            memory_ok = system_info['memory_percent'] < threshold_memory
            disk_ok = system_info['disk_percent'] < threshold_disk
            
            if not memory_ok:
                return False, f"Memory usage too high: {system_info['memory_percent']:.1f}%"
            if not disk_ok:
                return False, f"Disk usage too high: {system_info['disk_percent']:.1f}%"
            
            return True, "Resources OK"
            
        except Exception as e:
            logger.error(f"Error monitoring resources: {e}")
            return False, f"Monitoring error: {e}"
    
    async def optimize_download_path(self, base_path: str) -> str:
        """Optimize download path for best performance"""
        try:
            # Use fastest available storage
            paths_to_check = [
                "/tmp",  # RAM disk (fastest)
                "/var/tmp",  # Alternative temp
                "./downloads"  # Local directory
            ]
            
            best_path = base_path
            best_score = 0
            
            for path in paths_to_check:
                try:
                    path_obj = Path(path)
                    if path_obj.exists() and path_obj.is_dir():
                        # Check if we can write
                        test_file = path_obj / "test_write.tmp"
                        test_file.write_text("test")
                        test_file.unlink()
                        
                        # Score based on available space and speed
                        disk_usage = psutil.disk_usage(path)
                        free_space_gb = disk_usage.free / (1024**3)
                        
                        # Prefer RAM disk (/tmp) if available
                        score = free_space_gb
                        if path == "/tmp":
                            score *= 2  # Bonus for RAM disk
                        
                        if score > best_score:
                            best_score = score
                            best_path = path
                            
                except (OSError, PermissionError):
                    continue
            
            logger.info(f"Optimized download path: {best_path}")
            return best_path
            
        except Exception as e:
            logger.error(f"Error optimizing download path: {e}")
            return base_path

# Global instance
performance_optimizer = PerformanceOptimizer()
