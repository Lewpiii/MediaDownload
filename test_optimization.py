#!/usr/bin/env python3
"""
Test script for the Discord Media Download Bot
Tests all major functionality and optimizations
"""
import asyncio
import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.performance import performance_optimizer
from config import DOWNLOAD_CONFIG, RESOURCE_LIMITS
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test')

async def test_performance_optimizer():
    """Test the performance optimizer"""
    logger.info("Testing Performance Optimizer...")
    
    try:
        # Test system optimization
        await performance_optimizer.optimize_system()
        logger.info("✓ System optimization applied")
        
        # Test resource monitoring
        is_ok, message = await performance_optimizer.monitor_resources()
        logger.info(f"✓ Resource monitoring: {message}")
        
        # Test download path optimization
        optimized_path = await performance_optimizer.optimize_download_path("/tmp")
        logger.info(f"✓ Optimized download path: {optimized_path}")
        
        # Test system info
        system_info = performance_optimizer.get_system_info()
        logger.info(f"✓ System info retrieved: CPU {system_info.get('cpu_percent', 0):.1f}%, Memory {system_info.get('memory_percent', 0):.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Performance optimizer test failed: {e}")
        return False

async def test_download_config():
    """Test download configuration"""
    logger.info("Testing Download Configuration...")
    
    try:
        # Test temp directory creation
        temp_dir = DOWNLOAD_CONFIG['temp_dir']
        os.makedirs(temp_dir, exist_ok=True)
        
        if os.path.exists(temp_dir):
            logger.info(f"✓ Temp directory created: {temp_dir}")
        else:
            logger.error(f"✗ Failed to create temp directory: {temp_dir}")
            return False
        
        # Test chunk size
        chunk_size = DOWNLOAD_CONFIG['chunk_size']
        logger.info(f"✓ Chunk size configured: {chunk_size / (1024*1024):.1f}MB")
        
        # Test resource limits
        memory_threshold = RESOURCE_LIMITS['memory_threshold']
        disk_threshold = RESOURCE_LIMITS['disk_threshold']
        logger.info(f"✓ Resource limits: Memory {memory_threshold}%, Disk {disk_threshold}%")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Download config test failed: {e}")
        return False

async def test_system_resources():
    """Test system resource availability"""
    logger.info("Testing System Resources...")
    
    try:
        # Check memory
        memory = psutil.virtual_memory()
        logger.info(f"✓ Memory: {memory.available / (1024**3):.1f}GB available ({memory.percent:.1f}% used)")
        
        # Check disk space
        disk = psutil.disk_usage('/')
        logger.info(f"✓ Disk: {disk.free / (1024**3):.1f}GB free ({disk.percent:.1f}% used)")
        
        # Check CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        logger.info(f"✓ CPU: {cpu_percent:.1f}% usage")
        
        # Check if resources are within limits
        if memory.percent > RESOURCE_LIMITS['memory_threshold']:
            logger.warning(f"⚠ Memory usage high: {memory.percent:.1f}%")
        
        if disk.percent > RESOURCE_LIMITS['disk_threshold']:
            logger.warning(f"⚠ Disk usage high: {disk.percent:.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ System resources test failed: {e}")
        return False

async def test_file_operations():
    """Test file operations"""
    logger.info("Testing File Operations...")
    
    try:
        temp_dir = DOWNLOAD_CONFIG['temp_dir']
        test_file = os.path.join(temp_dir, "test_file.txt")
        
        # Test file creation
        with open(test_file, 'w') as f:
            f.write("Test content for optimization verification")
        
        if os.path.exists(test_file):
            logger.info("✓ File creation successful")
        else:
            logger.error("✗ File creation failed")
            return False
        
        # Test file reading
        with open(test_file, 'r') as f:
            content = f.read()
        
        if content == "Test content for optimization verification":
            logger.info("✓ File reading successful")
        else:
            logger.error("✗ File reading failed")
            return False
        
        # Cleanup
        os.remove(test_file)
        logger.info("✓ File cleanup successful")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ File operations test failed: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("Starting Discord Bot Optimization Tests...")
    logger.info("=" * 50)
    
    tests = [
        ("Performance Optimizer", test_performance_optimizer),
        ("Download Configuration", test_download_config),
        ("System Resources", test_system_resources),
        ("File Operations", test_file_operations)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning {test_name} test...")
        try:
            result = await test_func()
            if result:
                passed += 1
                logger.info(f"✓ {test_name} test PASSED")
            else:
                logger.error(f"✗ {test_name} test FAILED")
        except Exception as e:
            logger.error(f"✗ {test_name} test ERROR: {e}")
    
    logger.info("\n" + "=" * 50)
    logger.info(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Bot is optimized and ready.")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test suite error: {e}")
        sys.exit(1)
