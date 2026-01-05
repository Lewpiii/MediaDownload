#!/usr/bin/env python3
"""
Shim for backward compatibility.
Allows running the bot via 'python3 bot.py' as configured in the existing systemd service.
Redirects to the new src.bot module.
"""
import sys
import os

# Add current directory to path so we can import src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.bot import run

if __name__ == "__main__":
    run()
