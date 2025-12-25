"""
Utility functions for video processing
StreamFlash.sx integration
"""

import os
import subprocess
import requests
from config import (
    STREAMFLASH_API_URL,
    STREAMFLASH_API_KEY,
    THUMBNAIL_TIMESTAMP,
    THUMBNAIL_WIDTH,
    FFMPEG_PATH,
    TEMP_DOWNLOAD_PATH,
    TEMP_THUMBNAIL_PATH
)

# ============================================
# STREAMFLASH OPERATIONS
# ============================================

def upload_to_streamflash(video_path=None, video_url=None):
    """
    Upload video to StreamFlash API
    
    Args:
        video_path: Path to local video file (will be uploaded to get URL first)
        video_url: Direct download URL
        
    Returns:
        StreamFlash link or None if failed
    """
    
    if not STREAMFLASH_API_KEY:
        print("❌ StreamFlash API key not configured!")
        return None
    
    # StreamFlash API requires video URL, not file upload
    # So if we have a file path, we need to get its Telegram URL
    if video_path and not video_url:
        print("⚠️ StreamFlash requires URL upload")
        print("   File upload not supported, need Telegram file URL")
        return None
    
    if not video_url:
        print("❌ No video URL provided")
        return None
    
    try:
        print(f"📤 Uploading to StreamFlash...")
        print(f"   URL: {video_url}")
        print(f"   API: {STREAMFLASH_API_URL}")
        
        headers = {
            "Authorization": f"Bearer {STREAMFLASH_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "StreamFlash-Bot/1.0"
        }
        
        payload = {
            "url": video_url
        }
        
        response = requests.post(
            STREAMFLASH_API_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        print(f"   Response Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        
        # Check for errors
        if response.status_code == 401:
            print("❌ Authentication failed - Check API key")
            return None
        
        if response.status_code == 404:
            print("❌ Endpoint not found")
            return None
        
        if response.status_code == 503:
            print("❌ Service unavailable")
            return None
        
        # Parse response
        if response.status_code in [200, 201]:
            try:
                json_response = response.json()
                print(f"   Response: {json_response}")
                
                # Check if upload was successful
                if json_response.get("success"):
                    batch_id = json_response.get("batch_id")
                    queued = json_response.get("queued", 0)
                    
                    print(f"✅ Upload queued successfully!")
                    print(f"   Batch ID: {batch_id}")
                    print(f"   Queued: {queued}")
                    
                    # Need to check upload status to get final URL
                    # For now, return a placeholder or check status
                    video_link = get_upload_status(batch_id)
                    
                    return video_link
                else:
                    print(f"❌ Upload failed")
                    print(f"   Response: {json_response}")
                    return None
                    
            except ValueError as e:
                print(f"❌ Invalid JSON: {e}")
                print(f"   Response: {response.text[:500]}")
                return None
        else:
            print(f"❌ Upload failed: Status {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"❌ Upload timeout")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        return None
    except Exception as e:
        print(f"❌ Upload error: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_upload_status(batch_id):
    """
    Check upload status on StreamFlash
    
    Args:
        batch_id: Batch ID from remote upload
        
    Returns:
        Video URL when ready, or None
    """
    
    if not batch_id:
        return None
    
    try:
        # According to API docs: GET https://streamflash.sx/api/upload_status.php?api_key=KEY&batch_id=123
        status_url = f"https://streamflash.sx/api/upload_status.php?api_key={STREAMFLASH_API_KEY}&batch_id={batch_id}"
        
        print(f"   Checking upload status...")
        
        # Poll for status (wait up to 60 seconds)
        import time
        max_attempts = 12  # 12 attempts * 5 seconds = 60 seconds
        
        for attempt in range(max_attempts):
            response = requests.get(status_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    items = data.get("items", [])
                    
                    if items:
                        # Get first completed item
                        for item in items:
                            if item.get("status") == "done":
                                video_url = item.get("url")
                                video_id = item.get("video_id")
                                
                                print(f"✅ Upload completed!")
                                print(f"   Video ID: {video_id}")
                                print(f"   URL: {video_url}")
                                
                                return video_url
                        
                        # Check if still processing
                        if any(item.get("status") == "processing" for item in items):
                            print(f"   Still processing... (attempt {attempt + 1}/{max_attempts})")
                            time.sleep(5)
                            continue
                        
                        # Check for errors
                        errors = [item for item in items if item.get("errors", 0) > 0]
                        if errors:
                            print(f"❌ Upload had errors: {errors}")
                            return None
            
            time.sleep(5)
        
        print(f"⚠️ Upload status check timeout")
        return None
        
    except Exception as e:
        print(f"❌ Status check error: {e}")
        return None

# ============================================
# TELEGRAM FILE URL OPERATIONS
# ============================================

async def get_telegram_file_link(client, message):
    """
    Get Telegram file link for video
    StreamFlash needs a direct URL to download from
    
    Args:
        client: Pyrogram client
        message: Message with video/document
        
    Returns:
        Telegram file URL or None
    """
    try:
        # Get file
        if message.video:
            file = message.video
        elif message.document:
            file = message.document
        else:
            return None
        
        # Get file path
        file_id = file.file_id
        
        # Download to temp and re-upload to get public URL
        # OR use file.file_unique_id to construct Telegram CDN URL
        
        # For now, we'll download the file
        print(f"   Getting Telegram file for remote upload...")
        return None  # Will handle in handlers.py
        
    except Exception as e:
        print(f"❌ Error getting file link: {e}")
        return None

# ============================================
# THUMBNAIL OPERATIONS
# ============================================

def extract_thumbnail(video_path, output_filename=None):
    """Extract thumbnail from video using FFmpeg"""
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
            print(f"❌ Thumbnail not created")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error: {e.stderr}")
        return None
    except Exception as e:
        print(f"❌ Thumbnail error: {e}")
        return None

# ============================================
# TEXT PARSING
# ============================================

def extract_direct_link(message):
    """Extract direct download link from message"""
    text = message.text or message.caption or ""
    
    for word in text.split():
        if word.startswith('http://') or word.startswith('https://'):
            return word
    
    return None

def extract_video_title(message):
    """Extract video title from message caption"""
    if message.caption:
        title = message.caption.split('\n')[0]
        words = title.split()
        title = ' '.join([w for w in words if not w.startswith('http')])
        return title[:100]
    
    return "Adult Video"

# ============================================
# FILE OPERATIONS
# ============================================

def cleanup_temp_files(*file_paths):
    """Clean up temporary files"""
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🗑️ Cleaned up: {file_path}")
            except Exception as e:
                print(f"⚠️ Cleanup failed: {file_path}: {e}")

def get_file_size_mb(file_path):
    """Get file size in MB"""
    if os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        return f"{size_mb:.2f} MB"
    return "Unknown"
        
