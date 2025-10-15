import os
from typing import Iterable, List, Sequence, Tuple
from urllib.parse import urlparse

import discord


class MediaExtractor:
    """Utility to extract media URLs from a discord.Message without message content intent.

    It scans:
    - Attachments
    - Embeds (image, thumbnail, video, main url)

    Optionally, it can parse plain text links if provided externally, but by default we keep
    include_text_links=False to avoid relying on message content.
    """

    @staticmethod
    def _matches_allowed_ext(url: str, allowed_exts: Sequence[str]) -> Tuple[bool, str]:
        try:
            path = urlparse(url).path or ""
            ext = os.path.splitext(path)[1].lower()
            if ext and ext in allowed_exts:
                filename = os.path.basename(path) or f"file{ext}"
                return True, filename
        except Exception:
            pass
        return False, ""

    @staticmethod
    def extract(
        message: discord.Message,
        *,
        allowed_exts: Sequence[str],
        include_text_links: bool = False,
        extra_text_links: Iterable[str] | None = None,
    ) -> List[Tuple[str, str]]:
        candidates: List[Tuple[str, str]] = []

        # 1) Attachments
        try:
            for att in getattr(message, "attachments", []) or []:
                ext = os.path.splitext(att.filename)[1].lower()
                if ext in allowed_exts:
                    candidates.append((att.url, att.filename))
        except Exception:
            pass

        # 2) Embeds (image, thumbnail, video, main link)
        try:
            for emb in getattr(message, "embeds", []) or []:
                urls: List[str] = []
                if getattr(emb, "url", None):
                    urls.append(emb.url)
                if getattr(emb, "thumbnail", None) and getattr(emb.thumbnail, "url", None):
                    urls.append(emb.thumbnail.url)
                if getattr(emb, "image", None) and getattr(emb.image, "url", None):
                    urls.append(emb.image.url)
                if getattr(emb, "video", None) and getattr(emb.video, "url", None):
                    urls.append(emb.video.url)

                for u in urls:
                    ok, name = MediaExtractor._matches_allowed_ext(u, allowed_exts)
                    if ok:
                        candidates.append((u, name))
        except Exception:
            pass

        # 3) Optional explicit text links provided by caller (not message content)
        if include_text_links and extra_text_links:
            for u in extra_text_links:
                ok, name = MediaExtractor._matches_allowed_ext(u, allowed_exts)
                if ok:
                    candidates.append((u, name))

        return candidates

import os
import re
from typing import List, Tuple
import mimetypes
import os as _os
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

        # Config: relaxed mode to accept broader attachments during diagnosis
        relaxed = _os.getenv('RELAXED_ATTACHMENT_FILTER', 'false').lower() in ('1', 'true', 'yes')

        # 1) Native attachments
        for attachment in getattr(msg, 'attachments', []) or []:
            filename = getattr(attachment, 'filename', '') or f"attachment_{len(results)}"
            file_ext = os.path.splitext(filename)[1].lower()
            content_type = getattr(attachment, 'content_type', None)

            is_allowed_by_ext = file_ext in allowed_exts
            is_allowed_by_mime = False
            if content_type:
                major = content_type.split('/')[0]
                is_allowed_by_mime = major in ("image", "video")
                # if missing extension, try to infer from mime
                if not file_ext:
                    guessed = mimetypes.guess_extension(content_type) or ''
                    file_ext = guessed.lower()
                    if filename and not os.path.splitext(filename)[1] and guessed:
                        filename = f"{filename}{guessed}"

            if relaxed and getattr(attachment, 'url', None):
                # In relaxed mode, accept any attachment with a downloadable URL
                results.append((attachment.url, filename))
                continue

            if (is_allowed_by_ext or is_allowed_by_mime) and getattr(attachment, 'url', None):
                results.append((attachment.url, filename))

        # 2) Embeds (image/thumbnail/video/url)
        for emb in getattr(msg, 'embeds', []) or []:
            # Primary embed URL
            if getattr(emb, 'url', None) and cls._url_has_allowed_ext(emb.url, allowed_exts):
                results.append((emb.url, os.path.basename(urlparse(emb.url).path) or f"embed_{len(results)}"))

            # Image
            image = getattr(emb, 'image', None)
            if image:
                candidate_urls = [getattr(image, 'url', None), getattr(image, 'proxy_url', None)]
                for u in candidate_urls:
                    if u and cls._url_has_allowed_ext(u, allowed_exts):
                        results.append((u, os.path.basename(urlparse(u).path) or f"image_{len(results)}"))
                        break

            # Thumbnail
            thumb = getattr(emb, 'thumbnail', None)
            if thumb:
                candidate_urls = [getattr(thumb, 'url', None), getattr(thumb, 'proxy_url', None)]
                for u in candidate_urls:
                    if u and cls._url_has_allowed_ext(u, allowed_exts):
                        results.append((u, os.path.basename(urlparse(u).path) or f"thumb_{len(results)}"))
                        break

            # Video
            video = getattr(emb, 'video', None)
            if video:
                candidate_urls = [getattr(video, 'url', None), getattr(video, 'proxy_url', None)]
                for u in candidate_urls:
                    if u and cls._url_has_allowed_ext(u, allowed_exts):
                        results.append((u, os.path.basename(urlparse(u).path) or f"video_{len(results)}"))
                        break

        # 3) Optional: plain-text links (only if caller opts-in)
        if include_text_links:
            for link in cls._extract_links_from_text(getattr(msg, 'content', None)):
                if cls._url_has_allowed_ext(link, allowed_exts):
                    results.append((link, os.path.basename(urlparse(link).path) or f"link_{len(results)}"))

        return results


