import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from utils.smart_classifier import SmartClassifier

class TestSmartClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = SmartClassifier(minimum_files_per_category=3)

    def test_analyze_filename_game_keywords(self):
        """Test if game keywords are correctly identified"""
        category, sub, conf = self.classifier.analyze_filename("fortnite_clip.mp4")
        self.assertEqual(category, 'Games')
        self.assertEqual(sub, 'Fortnite')
        self.assertGreaterEqual(conf, 30.0)
        
        category, sub, conf = self.classifier.analyze_filename("valorant_ace.mp4")
        self.assertEqual(category, 'Games')
        self.assertEqual(sub, 'Valorant')

    def test_analyze_filename_app_keywords(self):
        """Test if app keywords are correctly identified"""
        category, sub, conf = self.classifier.analyze_filename("discord_chat.png")
        self.assertEqual(category, 'Apps')
        self.assertEqual(sub, 'Discord')

    def test_analyze_filename_unknown(self):
        """Test unknown files"""
        category, sub, conf = self.classifier.analyze_filename("random_file_xyz.txt")
        self.assertEqual(category, 'Other')
        self.assertEqual(sub, 'Miscellaneous')

    def test_organization_threshold(self):
        """Test if files are grouped correctly based on threshold"""
        files = [
            "path/to/fortnite_1.mp4",
            "path/to/fortnite_2.mp4",
            "path/to/fortnite_3.mp4",
            "path/to/random_1.jpg",
            "path/to/random_2.jpg"
        ]
        
        organized = self.classifier.organize_with_minimum_threshold(files)
        
        # Fortnite has 3 files, should be in Games/Fortnite
        self.assertIn('Games/Fortnite', organized)
        self.assertEqual(len(organized['Games/Fortnite']), 3)
        
        # Random files are < 3, should be in Other/Miscellaneous
        self.assertIn('Other/Miscellaneous', organized)
        self.assertEqual(len(organized['Other/Miscellaneous']), 2)

if __name__ == '__main__':
    unittest.main()
