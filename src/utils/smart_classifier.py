"""
Smart Media Classifier
Automatically categorizes media files and organizes them into folders
with intelligent grouping based on content analysis
"""
import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path
import json

logger = logging.getLogger('bot.classifier')

class SmartClassifier:
    def __init__(self, minimum_files_per_category: int = 3):
        self.minimum_files = minimum_files_per_category
        self.categories = self._load_categories()
        self.classification_cache = {}
        
    def _load_categories(self) -> Dict[str, Dict[str, List[str]]]:
        """Load predefined categories with keywords for classification"""
        return {
            'Games': {
                'Fortnite': ['fortnite', 'fortnitebr', 'fortnitebattle', 'victory', 'royale', 'battle', 'skins', 'emotes', 'skin', 'build', 'creative'],
                'Valorant': ['valorant', 'valorantgame', 'spike', 'agents', 'abilities', 'rounds', 'ranked'],
                'Minecraft': ['minecraft', 'mc', 'blocks', 'creeper', 'enderman', 'nether', 'end', 'diamond', 'screenshot'],
                'League of Legends': ['lol', 'league', 'legends', 'summoner', 'rift', 'champions', 'ranked', 'aram'],
                'CS:GO': ['csgo', 'cs2', 'counter', 'strike', 'terrorist', 'ct', 'bomb', 'defuse', 'awp'],
                'Apex Legends': ['apex', 'legends', 'battle', 'royale', 'champion', 'respawn', 'titanfall'],
                'Rocket League': ['rocket', 'league', 'car', 'ball', 'goal', 'boost', 'aerial', 'freestyle'],
                'Among Us': ['among', 'us', 'sus', 'impostor', 'crewmate', 'tasks', 'vent', 'kill'],
                'Genshin Impact': ['genshin', 'impact', 'anemo', 'pyro', 'hydro', 'electro', 'cryo', 'geo'],
                'Call of Duty': ['cod', 'call', 'duty', 'warzone', 'modern', 'warfare', 'black', 'ops'],
                'FIFA': ['fifa', 'football', 'soccer', 'goal', 'stadium', 'player', 'match'],
                'PUBG': ['pubg', 'battlegrounds', 'chicken', 'dinner', 'survival', 'zone'],
                'Overwatch': ['overwatch', 'ow', 'heroes', 'tank', 'dps', 'support', 'ult'],
                'World of Warcraft': ['wow', 'world', 'warcraft', 'alliance', 'horde', 'raid', 'dungeon'],
                'Destiny': ['destiny', 'guardian', 'light', 'darkness', 'raid', 'strike', 'crucible']
            },
            'Apps': {
                'Discord': ['discord', 'server', 'channel', 'voice', 'chat', 'bot', 'nitro'],
                'Photoshop': ['photoshop', 'ps', 'edit', 'layer', 'filter', 'brush', 'design'],
                'Premiere Pro': ['premiere', 'video', 'edit', 'timeline', 'clip', 'export', 'render'],
                'After Effects': ['after', 'effects', 'ae', 'motion', 'graphics', 'animation', 'keyframe'],
                'Blender': ['blender', '3d', 'modeling', 'animation', 'render', 'cycles', 'eevee'],
                'OBS': ['obs', 'streaming', 'recording', 'broadcast', 'studio', 'scene'],
                'Spotify': ['spotify', 'music', 'playlist', 'song', 'album', 'artist'],
                'Steam': ['steam', 'game', 'library', 'store', 'community', 'workshop'],
                'Twitch': ['twitch', 'stream', 'streamer', 'chat', 'follow', 'subscriber']
            },
            'Content': {
                'Memes': ['meme', 'funny', 'lol', 'haha', 'joke', 'comedy', 'humor', 'dank'],
                'Screenshots': ['screenshot', 'screen', 'capture', 'desktop', 'window', 'display'],
                'Clips': ['clip', 'highlight', 'moment', 'epic', 'fail', 'win', 'best'],
                'Tutorials': ['tutorial', 'guide', 'how', 'to', 'learn', 'teach', 'explain'],
                'Artwork': ['art', 'drawing', 'painting', 'sketch', 'digital', 'creative', 'artist'],
                'Wallpapers': ['wallpaper', 'background', 'desktop', 'screen', 'resolution', 'hd', '4k']
            },
            'Social': {
                'Instagram': ['instagram', 'insta', 'story', 'post', 'reel', 'follow'],
                'TikTok': ['tiktok', 'video', 'trend', 'dance', 'challenge', 'fyp'],
                'YouTube': ['youtube', 'yt', 'video', 'channel', 'subscribe', 'like'],
                'Twitter': ['twitter', 'tweet', 'retweet', 'like', 'follow', 'hashtag'],
                'Reddit': ['reddit', 'post', 'comment', 'upvote', 'downvote', 'subreddit']
            }
        }
    
    def analyze_filename(self, filename: str) -> Tuple[str, str, float]:
        """
        Analyze filename and return (category, subcategory, confidence)
        """
        filename_lower = filename.lower()
        
        # Remove common file extensions and numbers
        clean_name = re.sub(r'[0-9]+', '', filename_lower)
        clean_name = re.sub(r'[._-]', ' ', clean_name)
        
        best_match = None
        best_score = 0.0
        
        for category, subcategories in self.categories.items():
            for subcategory, keywords in subcategories.items():
                score = 0
                total_keywords = len(keywords)
                
                for keyword in keywords:
                    if keyword in clean_name:
                        # Exact match gets higher score
                        if keyword == clean_name.strip():
                            score += 2.0
                        else:
                            score += 1.0
                
                # Calculate confidence as percentage (minimum 30% to be considered)
                confidence = (score / total_keywords) * 100
                if score > 0 and confidence < 30:
                    confidence = 30  # Minimum confidence for any match
                
                if confidence > best_score:
                    best_score = confidence
                    best_match = (category, subcategory, confidence)
        
        # If no good match found, return generic category
        if best_score < 30:  # Minimum confidence threshold
            return 'Other', 'Miscellaneous', 50.0
        
        return best_match
    
    def classify_files(self, files: List[str]) -> Dict[str, List[str]]:
        """
        Classify a list of files and group them by category
        Returns dict with category/subcategory as key and list of files as value
        """
        classification_results = defaultdict(list)
        
        for file_path in files:
            filename = os.path.basename(file_path)
            category, subcategory, confidence = self.analyze_filename(filename)
            
            # Create folder structure: Category/Subcategory
            folder_key = f"{category}/{subcategory}"
            classification_results[folder_key].append(file_path)
            
            logger.debug(f"Classified '{filename}' as {folder_key} (confidence: {confidence:.1f}%)")
        
        return dict(classification_results)
    
    def organize_with_minimum_threshold(self, files: List[str]) -> Dict[str, List[str]]:
        """
        Organize files with minimum threshold per category
        Categories with less than minimum_files go to 'Other'
        """
        # First, classify all files
        classified = self.classify_files(files)
        
        # Count files per category (not subcategory)
        category_counts = defaultdict(int)
        category_files = defaultdict(list)
        
        for folder_key, file_list in classified.items():
            category = folder_key.split('/')[0]
            category_counts[category] += len(file_list)
            category_files[category].extend(file_list)
        
        # Reorganize based on minimum threshold
        final_organization = {}
        other_files = []
        
        for category, count in category_counts.items():
            if count >= self.minimum_files:
                # Keep original subcategory organization for this category
                for folder_key, file_list in classified.items():
                    if folder_key.startswith(f"{category}/"):
                        final_organization[folder_key] = file_list
            else:
                # Move to Other category
                other_files.extend(category_files[category])
                logger.info(f"Category '{category}' has only {count} files (< {self.minimum_files}), moving to Other")
        
        # Add Other category if there are files
        if other_files:
            final_organization['Other/Miscellaneous'] = other_files
        
        return final_organization
    
    def create_folder_structure(self, organized_files: Dict[str, List[str]], base_path: str) -> Dict[str, str]:
        """
        Create actual folder structure and return mapping of files to their new paths
        """
        file_mapping = {}
        
        for folder_key, file_list in organized_files.items():
            # Create folder path
            folder_path = os.path.join(base_path, folder_key)
            os.makedirs(folder_path, exist_ok=True)
            
            logger.info(f"Created folder: {folder_path} with {len(file_list)} files")
            
            # Move files to new location
            for file_path in file_list:
                filename = os.path.basename(file_path)
                new_path = os.path.join(folder_path, filename)
                
                # Handle duplicate filenames
                counter = 1
                original_new_path = new_path
                while os.path.exists(new_path):
                    name, ext = os.path.splitext(filename)
                    new_path = os.path.join(folder_path, f"{name}_{counter}{ext}")
                    counter += 1
                
                file_mapping[file_path] = new_path
        
        return file_mapping
    
    def get_organization_stats(self, organized_files: Dict[str, List[str]]) -> Dict:
        """Get statistics about the organization"""
        stats = {
            'total_files': sum(len(files) for files in organized_files.values()),
            'total_categories': len(organized_files),
            'categories': {}
        }
        
        for folder_key, file_list in organized_files.items():
            category, subcategory = folder_key.split('/', 1)
            if category not in stats['categories']:
                stats['categories'][category] = {}
            stats['categories'][category][subcategory] = len(file_list)
        
        return stats
    
    def save_classification_log(self, organized_files: Dict[str, List[str]], log_path: str):
        """Save classification results to a log file"""
        stats = self.get_organization_stats(organized_files)
        
        log_data = {
            'timestamp': str(Path().cwd()),
            'minimum_threshold': self.minimum_files,
            'stats': stats,
            'organization': organized_files
        }
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Classification log saved to: {log_path}")

# Global instance
smart_classifier = SmartClassifier(minimum_files_per_category=3)
