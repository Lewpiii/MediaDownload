#!/usr/bin/env python3
"""
Test script for the Smart Classification System
Tests the intelligent file organization with various scenarios
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.smart_classifier import smart_classifier
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_classification')

def test_basic_classification():
    """Test basic classification functionality"""
    logger.info("Testing Basic Classification...")
    
    test_files = [
        "fortnite_victory_royale.mp4",
        "minecraft_build_tutorial.jpg", 
        "valorant_spike_defuse.png",
        "discord_screenshot.png",
        "photoshop_edit_final.jpg",
        "random_meme_funny.gif",
        "unknown_file.mp4",
        "another_random.jpg",
        "fortnite_skin_new.png",
        "minecraft_creeper_art.jpg",
        "valorant_agent_abilities.mp4"
    ]
    
    # Test classification
    organized = smart_classifier.organize_with_minimum_threshold(test_files)
    stats = smart_classifier.get_organization_stats(organized)
    
    logger.info(f"✓ Classified {stats['total_files']} files into {stats['total_categories']} categories")
    
    # Show results
    for folder_key, files in organized.items():
        logger.info(f"📁 {folder_key}: {len(files)} files")
        for file in files:
            logger.info(f"  - {file}")
    
    return len(organized) > 0

def test_minimum_threshold():
    """Test minimum threshold functionality"""
    logger.info("Testing Minimum Threshold (3 files)...")
    
    # Files that should create categories (3+ files each)
    fortnite_files = [
        "fortnite_victory_royale.mp4",
        "fortnite_skin_new.png", 
        "fortnite_build_creative.jpg",
        "fortnite_emote_dance.gif"
    ]
    
    # Files that should go to Other (< 3 files)
    single_files = [
        "minecraft_screenshot.jpg",
        "valorant_clip.mp4"
    ]
    
    all_files = fortnite_files + single_files
    organized = smart_classifier.organize_with_minimum_threshold(all_files)
    
    # Check if Fortnite category was created (3+ files)
    fortnite_created = any("Fortnite" in key for key in organized.keys())
    
    # Check if Other category exists for single files
    other_exists = "Other/Miscellaneous" in organized
    
    logger.info(f"✓ Fortnite category created: {fortnite_created}")
    logger.info(f"✓ Other category exists: {other_exists}")
    
    # Show detailed results
    for folder_key, files in organized.items():
        logger.info(f"📁 {folder_key}: {len(files)} files")
    
    return fortnite_created and other_exists

def test_edge_cases():
    """Test edge cases and special scenarios"""
    logger.info("Testing Edge Cases...")
    
    edge_cases = [
        "123456789.mp4",  # Numbers only
        "file_with_underscores_and-dashes.jpg",  # Mixed separators
        "UPPERCASE_FILENAME.PNG",  # Uppercase
        "file.with.many.dots.gif",  # Multiple dots
        "very_long_filename_with_many_words_that_should_still_be_classified.mp4"
    ]
    
    organized = smart_classifier.organize_with_minimum_threshold(edge_cases)
    
    logger.info(f"✓ Processed {len(edge_cases)} edge case files")
    
    # All should go to Other since they don't match any category
    all_in_other = all("Other" in key for key in organized.keys())
    logger.info(f"✓ All edge cases in Other category: {all_in_other}")
    
    return all_in_other

def test_category_coverage():
    """Test coverage of different categories"""
    logger.info("Testing Category Coverage...")
    
    # Ensure we have enough files per category (3+ each)
    category_tests = {
        'Games': [
            "fortnite_battle.mp4",
            "fortnite_skin.png",
            "fortnite_victory.jpg",
            "minecraft_build.jpg",
            "minecraft_creeper.png",
            "minecraft_diamond.mp4"
        ],
        'Apps': [
            "discord_screenshot.png",
            "discord_chat.jpg",
            "discord_voice.mp4",
            "photoshop_edit.jpg",
            "photoshop_layer.png",
            "photoshop_filter.gif"
        ],
        'Content': [
            "meme_funny.gif",
            "meme_dank.jpg",
            "meme_lol.png",
            "tutorial_guide.mp4",
            "tutorial_howto.jpg",
            "tutorial_step.png"
        ]
    }
    
    all_files = []
    for category_files in category_tests.values():
        all_files.extend(category_files)
    
    organized = smart_classifier.organize_with_minimum_threshold(all_files)
    stats = smart_classifier.get_organization_stats(organized)
    
    logger.info(f"✓ Tested {len(category_tests)} main categories")
    logger.info(f"✓ Created {stats['total_categories']} organized categories")
    
    # Check if main categories were created
    categories_created = set()
    for folder_key in organized.keys():
        category = folder_key.split('/')[0]
        categories_created.add(category)
    
    logger.info(f"✓ Categories created: {categories_created}")
    
    # Show detailed organization
    for folder_key, files in organized.items():
        logger.info(f"📁 {folder_key}: {len(files)} files")
    
    return len(categories_created) > 0

def main():
    """Run all classification tests"""
    logger.info("Starting Smart Classification Tests...")
    logger.info("=" * 60)
    
    tests = [
        ("Basic Classification", test_basic_classification),
        ("Minimum Threshold", test_minimum_threshold),
        ("Edge Cases", test_edge_cases),
        ("Category Coverage", test_category_coverage)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning {test_name} test...")
        try:
            result = test_func()
            if result:
                passed += 1
                logger.info(f"✓ {test_name} test PASSED")
            else:
                logger.error(f"✗ {test_name} test FAILED")
        except Exception as e:
            logger.error(f"✗ {test_name} test ERROR: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"Classification Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All classification tests passed! Smart organization is ready.")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    try:
        result = main()
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test suite error: {e}")
        sys.exit(1)
