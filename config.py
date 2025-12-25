"""
Configuration settings for StreamFlash Telegram Bot
Edit this file to customize bot behavior
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================
# TELEGRAM CONFIGURATION
# ============================================

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

# ============================================
# CHANNEL CONFIGURATION
# ============================================

FILE_STORE_CHANNEL = int(os.getenv("FILE_STORE_CHANNEL", "0"))
MAIN_CHANNEL = os.getenv("MAIN_CHANNEL", "")

# ============================================
# STREAMFLASH CONFIGURATION
# ============================================

STREAMFLASH_API_URL = "https://streamflash.sx/api/remote_upload.php"
STREAMFLASH_API_KEY = os.getenv("STREAMFLASH_API_KEY", "")

# ============================================
# DATABASE CONFIGURATION
# ============================================

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "video_automation")

# ============================================
# POSTING CONFIGURATION
# ============================================

DEFAULT_POSTING_INTERVAL = int(os.getenv("DEFAULT_POSTING_INTERVAL", "6"))

# ============================================
# VIDEO PROCESSING SETTINGS
# ============================================

THUMBNAIL_TIMESTAMP = "00:00:05"  # Extract thumbnail at 5 seconds
THUMBNAIL_WIDTH = 1280  # HD quality
TEMP_DOWNLOAD_PATH = "temp_downloads/"
TEMP_THUMBNAIL_PATH = "temp_thumbnails/"

# ============================================
# FFMPEG CONFIGURATION
# ============================================

FFMPEG_PATH = "ffmpeg"  # Use system ffmpeg

# ============================================
# VALIDATION
# ============================================

def validate_config():
    """Validate all required configuration"""
    errors = []
    
    if not API_ID or API_ID == 0:
        errors.append("API_ID is required")
    
    if not API_HASH:
        errors.append("API_HASH is required")
    
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN is required")
    
    if not ADMIN_USER_ID or ADMIN_USER_ID == 0:
        errors.append("ADMIN_USER_ID is required")
    
    if not FILE_STORE_CHANNEL or FILE_STORE_CHANNEL == 0:
        errors.append("FILE_STORE_CHANNEL is required")
    
    if not MAIN_CHANNEL:
        errors.append("MAIN_CHANNEL is required")
    
    if not STREAMFLASH_API_KEY:
        errors.append("STREAMFLASH_API_KEY is required")
    
    if errors:
        print("❌ Configuration Errors:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    return True

# Create temp directories
os.makedirs(TEMP_DOWNLOAD_PATH, exist_ok=True)
os.makedirs(TEMP_THUMBNAIL_PATH, exist_ok=True)
