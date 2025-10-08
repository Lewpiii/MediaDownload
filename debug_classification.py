#!/usr/bin/env python3
"""
Debug script for Smart Classification System
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.smart_classifier import smart_classifier

# Test simple
test_files = [
    "fortnite_victory_royale.mp4",
    "fortnite_skin_new.png", 
    "fortnite_build_creative.jpg",
    "minecraft_screenshot.jpg",
    "valorant_clip.mp4"
]

print("Testing classification...")
print(f"Files: {test_files}")

# Test individual classification
print("\nIndividual classification:")
for file in test_files:
    category, subcategory, confidence = smart_classifier.analyze_filename(file)
    print(f"{file} -> {category}/{subcategory} ({confidence:.1f}%)")

# Test grouping
print("\nGrouping with minimum threshold:")
organized = smart_classifier.organize_with_minimum_threshold(test_files)

for folder_key, files in organized.items():
    print(f"📁 {folder_key}: {len(files)} files")
    for file in files:
        print(f"  - {file}")
