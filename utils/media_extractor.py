import os
import re
from typing import List, Tuple
from urllib.parse import urlparse


class MediaExtractor:
    """Extract media URLs from a Discord message without requiring message content intent.

    It supports:
    - Native attachments (always available)
    - Embeds: image, thumbnail, video, and embed.url when it points to a direct media file
    - Optionally, plain-text links from message content if provided by caller (disabled by default)
    """

    @staticmethod
    def _url_has_allowed_ext(url: str, allowed_exts: List[str]) -> bool:
        try:
            path = urlparse(url).path
            return os.path.splitext(path)[1].lower() in allowed_exts
        except Exception:
            return False

    @staticmethod
    def _extract_links_from_text(text: str) -> List[str]:
        if not text:
            return []
        return [m.group(0) for m in re.finditer(r"https?://\S+", text)]

    @classmethod
    def extract(cls, msg, allowed_exts: List[str], include_text_links: bool = False) -> List[Tuple[str, str]]:
        """Return list of (url, suggested_filename) for media in a message.

        - allowed_exts: list of file extensions like ['.png', '.jpg', '.mp4']
        - include_text_links: if True, parse msg.content for direct media links (requires message content access)
        """
        results: List[Tuple[str, str]] = []

        # 1) Native attachments
        for attachment in getattr(msg, 'attachments', []) or []:
            filename = getattr(attachment, 'filename', '') or f"attachment_{len(results)}"
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in allowed_exts and getattr(attachment, 'url', None):
                results.append((attachment.url, filename))

        # 2) Embeds (image/thumbnail/video/url)
        for emb in getattr(msg, 'embeds', []) or []:
            # Primary embed URL
            if getattr(emb, 'url', None) and cls._url_has_allowed_ext(emb.url, allowed_exts):
                results.append((emb.url, os.path.basename(urlparse(emb.url).path) or f"embed_{len(results)}"))

            # Image
            image = getattr(emb, 'image', None)
            if image and getattr(image, 'url', None) and cls._url_has_allowed_ext(image.url, allowed_exts):
                results.append((image.url, os.path.basename(urlparse(image.url).path) or f"image_{len(results)}"))

            # Thumbnail
            thumb = getattr(emb, 'thumbnail', None)
            if thumb and getattr(thumb, 'url', None) and cls._url_has_allowed_ext(thumb.url, allowed_exts):
                results.append((thumb.url, os.path.basename(urlparse(thumb.url).path) or f"thumb_{len(results)}"))

            # Video
            video = getattr(emb, 'video', None)
            if video and getattr(video, 'url', None) and cls._url_has_allowed_ext(video.url, allowed_exts):
                results.append((video.url, os.path.basename(urlparse(video.url).path) or f"video_{len(results)}"))

        # 3) Optional: plain-text links (only if caller opts-in)
        if include_text_links:
            for link in cls._extract_links_from_text(getattr(msg, 'content', None)):
                if cls._url_has_allowed_ext(link, allowed_exts):
                    results.append((link, os.path.basename(urlparse(link).path) or f"link_{len(results)}"))

        return results


