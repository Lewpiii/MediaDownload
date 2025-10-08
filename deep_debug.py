#!/usr/bin/env python3
"""
Deep debug script for Smart Classification System
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.smart_classifier import smart_classifier
import re

# Test simple
filename = "fortnite_victory_royale.mp4"
print(f"Testing filename: {filename}")

# Debug the analysis process
filename_lower = filename.lower()
print(f"Lowercase: {filename_lower}")

# Remove common file extensions and numbers
clean_name = re.sub(r'[0-9]+', '', filename_lower)
clean_name = re.sub(r'[._-]', ' ', clean_name)
print(f"Clean name: '{clean_name}'")

# Test keyword matching
fortnite_keywords = ['fortnite', 'fortnitebr', 'fortnitebattle', 'victory', 'royale', 'battle', 'skins', 'emotes', 'skin', 'build', 'creative']
print(f"Fortnite keywords: {fortnite_keywords}")

for keyword in fortnite_keywords:
    if keyword in clean_name:
        print(f"✓ Found keyword '{keyword}' in '{clean_name}'")
    else:
        print(f"✗ Keyword '{keyword}' not found in '{clean_name}'")

# Test the actual classification
category, subcategory, confidence = smart_classifier.analyze_filename(filename)
print(f"\nFinal result: {category}/{subcategory} ({confidence:.1f}%)")
