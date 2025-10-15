Project Structure Overview

- bot.py: Bot bootstrap, intents, cog loading, status rotation, logging hooks
- cogs/
  - download.py: Slash commands and download workflow (history scan, media extraction, zipping, upload)
  - help.py, stats.py, feedback.py: Auxiliary cogs
- utils/
  - media_extractor.py: Collect media from attachments and embeds (no message content needed)
  - interactive_menu.py: UI flow for /download options and confirmation
  - smart_classifier.py: Organize files into categories; stats helpers
  - catbox.py: Upload large files when too big for Discord
  - performance.py: Safe performance tweaks (Windows-friendly) and housekeeping
  - logging.py: Logging helpers
  - topgg_checker.py: Optional top.gg vote checks
  - general.py, plots.py, torch_utils.py, model_loader.py, autoanchor.py, ai_detector.py, download_utils.py: legacy/advanced helpers (unused in default flow)

Key Design Decisions

- Minimal intents: messages intent not required. We read channel history via API and extract media from attachments and embeds. Optional ENABLE_MESSAGE_CONTENT=true enables reading plain text links if you have the privileged intent.
- Media extraction: utils/media_extractor.py centralizes attachment + embed URL discovery to keep cogs/download.py simple.
- Large outputs: if ZIP exceeds Discord’s limit, we upload using Catbox and return a link.
- Windows-safe: performance tweaks skip OS priority on Windows to avoid permission warnings.

Suggested Cleanup Policy

- Keep active: media_extractor.py, interactive_menu.py, smart_classifier.py, catbox.py, performance.py
- Evaluate/Archive: ai_detector.py, autoanchor.py, download_utils.py, model_loader.py, torch_utils.py, plots.py, general.py if not needed; move to archive/ and remove imports if confirmed unused.

How to Extend

- To support text link scraping: set ENABLE_MESSAGE_CONTENT=true and enable Message Content Intent in the Discord Developer Portal; then call MediaExtractor.extract(..., include_text_links=True).


