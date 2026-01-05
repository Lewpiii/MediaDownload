import unittest
import sys
import os
from unittest.mock import MagicMock

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from utils.media_extractor import MediaExtractor

class TestMediaExtractor(unittest.TestCase):
    def test_extract_attachments(self):
        """Test extraction from attachments"""
        msg = MagicMock()
        att = MagicMock()
        att.filename = "image.png"
        att.url = "http://example.com/image.png"
        att.content_type = "image/png"
        msg.attachments = [att]
        msg.embeds = []
        
        results = MediaExtractor.extract(msg, allowed_exts=['.png'])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "http://example.com/image.png")

    def test_extract_embeds(self):
        """Test extraction from embeds"""
        msg = MagicMock()
        msg.attachments = []
        embed = MagicMock()
        embed.url = "http://example.com/image.jpg"
        embed.image.url = "http://example.com/embedded_image.jpg"
        msg.embeds = [embed]
        
        results = MediaExtractor.extract(msg, allowed_exts=['.jpg'])
        # Expect at least one result (image or url)
        self.assertTrue(len(results) > 0)
        urls = [r[0] for r in results]
        self.assertIn("http://example.com/embedded_image.jpg", urls)

    def test_no_message_content_access(self):
        """Ensure it doesn't crash if content is missing (simulating no intent)"""
        msg = MagicMock()
        del msg.content # Simulate attribute error on access if property, or just None
        # Actually MagicMock allows access by default, so we need to ensure extract doesn't try to access it if include_text_links=False
        
        # We can't strict verify attribute access easily without complex mocking, 
        # but we can verify it works without 'content'
        msg.attachments = []
        msg.embeds = []
        
        try:
            MediaExtractor.extract(msg, allowed_exts=['.png'], include_text_links=False)
        except AttributeError:
            self.fail("MediaExtractor tried to access attributes it shouldn't have")

if __name__ == '__main__':
    unittest.main()
