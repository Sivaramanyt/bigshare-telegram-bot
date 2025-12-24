"""
Utility functions for video processing
"""

import os
import subprocess
import requests
from config import (
    BIGSHARE_API_URL,
    BIGSHARE_TOKEN,
    THUMBNAIL_TIMESTAMP,
    THUMBNAIL_WIDTH,
    FFMPEG_PATH,
    TEMP_DOWNLOAD_PATH,
    TEMP_THUMBNAIL_PATH
)

# ============================================
# BIGSHARE OPERATIONS
# ============================================

def upload_to_bigshare(video_path=None, video_url=None):
    """
    Upload video to BigShare API
    
    Args:
        video_path: Path to local video file
        video_url: Direct download URL
        
    Returns:
        BigShare link or None if failed
    """
    headers = {"Authorization": f"Bearer {BIGSHARE_TOKEN}"}
    
    try:
        if video_path:
            print(f"📤 Uploading file to BigShare...")
            with open(video_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    BIGSHARE_API_URL,
                    headers=headers,
                    files=files,
                    timeout=600
                )
        elif video_url:
            print(f"📤 Uploading URL to BigShare...")
            data = {'url': video_url}
            response = requests.post(
                BIGSHARE_API_URL,
                headers=headers,
                data=data,
                timeout=600
            )
        else:
            return None
        
        if response.status_code == 200:
            link = response.json().get('url') or response.json().get('link')
            print(f"✅ BigShare upload successful!")
            return link
        else:
            print(f"❌ BigShare upload failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

# ============================================
# THUMBNAIL OPERATIONS
# ============================================

def extract_thumbnail(video_path, output_filename=None):
    """
    Extract thumbnail from video using FFmpeg
    
    Args:
        video_path: Path to video file
        output_filename: Custom output filename (optional)
        
    Returns:
        Path to thumbnail or None if failed
    """
    if not output_filename:
        output_filename = f"thumb_{os.path.basename(video_path)}.jpg"
    
    output_path = os.path.join(TEMP_THUMBNAIL_PATH, output_filename)
    
    try:
        cmd = [
            FFMPEG_PATH,
            '-i', video_path,
            '-ss', THUMBNAIL_TIMESTAMP,
            '-vframes', '1',
            '-vf', f'scale={THUMBNAIL_WIDTH}:-1',
            '-y',
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        if os.path.exists(output_path):
            print(f"✅ Thumbnail extracted: {output_path}")
            return output_path
        else:
            print(f"❌ Thumbnail file not created")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error: {e.stderr}")
        return None
    except Exception as e:
        print(f"❌ Thumbnail extraction error: {e}")
        return None

# ============================================
# TEXT PARSING
# ============================================

def extract_direct_link(message):
    """
    Extract direct download link from message
    
    Args:
        message: Pyrogram message object
        
    Returns:
        URL string or None
    """
    text = message.text or message.caption or ""
    
    for word in text.split():
        if word.startswith('http://') or word.startswith('https://'):
            return word
    
    return None

def extract_video_title(message):
    """
    Extract video title from message caption
    
    Args:
        message: Pyrogram message object
        
    Returns:
        Video title string
    """
    if message.caption:
        # Take first line as title
        title = message.caption.split('\n')[0]
        # Remove URLs from title
        words = title.split()
        title = ' '.join([w for w in words if not w.startswith('http')])
        return title[:100]  # Max 100 chars
    
    return "Adult Video"

# ============================================
# FILE OPERATIONS
# ============================================

def cleanup_temp_files(*file_paths):
    """
    Clean up temporary files
    
    Args:
        *file_paths: Variable number of file paths to delete
    """
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🗑️ Cleaned up: {file_path}")
            except Exception as e:
                print(f"⚠️ Cleanup failed for {file_path}: {e}")

def get_file_size_mb(file_path):
    """Get file size in MB"""
    if os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        return f"{size_mb:.2f} MB"
    return "Unknown"
