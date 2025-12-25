"""
Utility functions for video processing
StreamFlash.sx integration
"""

import os
import subprocess
import requests
import time
from config import (
    STREAMFLASH_API_KEY,
    THUMBNAIL_TIMESTAMP,
    THUMBNAIL_WIDTH,
    FFMPEG_PATH,
    TEMP_DOWNLOAD_PATH,
    TEMP_THUMBNAIL_PATH
)

# StreamFlash API endpoints
STREAMFLASH_UPLOAD_URL = "https://streamflash.sx/api/remote_upload.php"
STREAMFLASH_STATUS_URL = "https://streamflash.sx/api/upload_status.php"

# ============================================
# STREAMFLASH OPERATIONS
# ============================================

def upload_to_streamflash(video_path=None, video_url=None):
    """
    Upload video to StreamFlash API
    
    Args:
        video_path: Path to local video file (not supported by StreamFlash)
        video_url: Direct download URL
        
    Returns:
        StreamFlash link or None if failed
    """
    
    if not STREAMFLASH_API_KEY:
        print("❌ StreamFlash API key not configured!")
        return None
    
    # StreamFlash only supports URL upload
    if video_path and not video_url:
        print("⚠️ StreamFlash requires URL upload, not file upload")
        return None
    
    if not video_url:
        print("❌ No video URL provided")
        return None
    
    try:
        print(f"📤 Uploading to StreamFlash...")
        print(f"   URL: {video_url[:80]}...")
        print(f"   API: {STREAMFLASH_UPLOAD_URL}")
        
        # Prepare headers with Bearer token
        headers = {
            "Authorization": f"Bearer {STREAMFLASH_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "StreamFlash-Bot/1.0"
        }
        
        # Prepare payload
        payload = {
            "url": video_url
        }
        
        # Make API request
        response = requests.post(
            STREAMFLASH_UPLOAD_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        print(f"   Response Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        
        # Handle different status codes
        if response.status_code == 401:
            print("❌ Authentication failed!")
            print("   Check if API key is correct")
            return None
        
        if response.status_code == 403:
            print("❌ Access forbidden!")
            print("   API key may be invalid or expired")
            return None
        
        if response.status_code == 404:
            print("❌ Endpoint not found!")
            print("   API URL may be incorrect")
            return None
        
        if response.status_code == 503:
            print("❌ Service unavailable!")
            print("   StreamFlash server may be down")
            return None
        
        if response.status_code == 422:
            print("❌ Invalid request!")
            try:
                error_data = response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Response: {response.text[:200]}")
            return None
        
        # Parse successful response
        if response.status_code in [200, 201]:
            try:
                json_response = response.json()
                print(f"   Response Data: {json_response}")
                
                # Check if upload was successful
                if json_response.get("success"):
                    batch_id = json_response.get("batch_id")
                    queued = json_response.get("queued", 0)
                    
                    print(f"✅ Upload queued successfully!")
                    print(f"   Batch ID: {batch_id}")
                    print(f"   Queued: {queued} video(s)")
                    
                    # Check upload status to get final URL
                    if batch_id:
                        video_link = get_upload_status(batch_id)
                        return video_link
                    else:
                        print(f"❌ No batch_id in response")
                        return None
                else:
                    print(f"❌ Upload failed!")
                    error_msg = json_response.get("error", "Unknown error")
                    print(f"   Error: {error_msg}")
                    return None
                    
            except ValueError as e:
                print(f"❌ Invalid JSON response: {e}")
                print(f"   Response: {response.text[:500]}")
                return None
        else:
            print(f"❌ Upload failed with status {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"❌ Upload request timeout")
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
    Polls the status endpoint until upload is complete
    
    Args:
        batch_id: Batch ID from remote upload
        
    Returns:
        Video URL when ready, or None if failed
    """
    
    if not batch_id:
        print("   ⚠️ No batch_id provided")
        return None
    
    try:
        print(f"   📊 Checking upload status...")
        print(f"   Batch ID: {batch_id}")
        
        # Prepare request parameters
        params = {
            "api_key": STREAMFLASH_API_KEY,
            "batch_id": batch_id
        }
        
        # Poll for status (max 2 minutes)
        max_attempts = 24  # 24 attempts * 5 seconds = 2 minutes
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(
                    STREAMFLASH_STATUS_URL,
                    params=params,
                    timeout=10
                )
                
                print(f"   Attempt {attempt + 1}/{max_attempts}: Status {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success"):
                        total = data.get("total", 0)
                        done = data.get("done", 0)
                        errors = data.get("errors", 0)
                        items = data.get("items", [])
                        
                        print(f"   Progress: {done}/{total} (errors: {errors})")
                        
                        if items:
                            # Check each item in the batch
                            for item in items:
                                item_id = item.get("id")
                                status = item.get("status")
                                url = item.get("url")
                                video_id = item.get("video_id")
                                message = item.get("message")
                                
                                print(f"   Item {item_id}: {status}")
                                
                                if status == "done" and url:
                                    print(f"   ✅ Upload completed!")
                                    print(f"   Video ID: {video_id}")
                                    print(f"   URL: {url}")
                                    return url
                                
                                elif status == "processing":
                                    print(f"   ⏳ Still processing...")
                                    
                                elif status == "error":
                                    print(f"   ❌ Upload error: {message}")
                                    return None
                            
                            # If no completed items yet, wait and retry
                            if done < total and attempt < max_attempts - 1:
                                print(f"   ⏳ Waiting 5 seconds before retry...")
                                time.sleep(5)
                                continue
                            elif done == 0 and errors == 0:
                                # Still processing
                                if attempt < max_attempts - 1:
                                    time.sleep(5)
                                    continue
                        else:
                            print(f"   ⚠️ No items in batch")
                            return None
                    else:
                        print(f"   ❌ API returned success=false")
                        error = data.get("error", "Unknown error")
                        print(f"   Error: {error}")
                        return None
                
                elif response.status_code == 404:
                    print(f"   ❌ Batch not found")
                    return None
                    
                else:
                    print(f"   ⚠️ Unexpected status: {response.status_code}")
                    if attempt < max_attempts - 1:
                        time.sleep(5)
                        continue
                    return None
                    
            except requests.exceptions.Timeout:
                print(f"   ⚠️ Status check timeout on attempt {attempt + 1}")
                if attempt < max_attempts - 1:
                    time.sleep(5)
                    continue
                return None
                
            except Exception as e:
                print(f"   ⚠️ Error on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(5)
                    continue
                return None
        
        print(f"   ⚠️ Timeout: Upload did not complete in 2 minutes")
        return None
        
    except Exception as e:
        print(f"❌ Status check error: {e}")
        import traceback
        traceback.print_exc()
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
        # FFmpeg command to extract frame
        cmd = [
            FFMPEG_PATH,
            '-i', video_path,
            '-ss', THUMBNAIL_TIMESTAMP,
            '-vframes', '1',
            '-vf', f'scale={THUMBNAIL_WIDTH}:-1',
            '-y',
            output_path
        ]
        
        # Run FFmpeg
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        # Check if thumbnail was created
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ Thumbnail extracted: {output_path} ({file_size} bytes)")
            return output_path
        else:
            print(f"❌ Thumbnail file not created")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error:")
        print(f"   Command: {' '.join(cmd)}")
        print(f"   Error: {e.stderr}")
        return None
    except FileNotFoundError:
        print(f"❌ FFmpeg not found!")
        print(f"   Make sure FFmpeg is installed and in PATH")
        return None
    except Exception as e:
        print(f"❌ Thumbnail extraction error: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================
# TEXT PARSING
# ============================================

def extract_direct_link(message):
    """
    Extract direct download link from message caption or text
    
    Args:
        message: Pyrogram message object
        
    Returns:
        URL string or None
    """
    text = message.text or message.caption or ""
    
    # Look for URLs in the text
    for word in text.split():
        if word.startswith('http://') or word.startswith('https://'):
            # Make sure it's a video link, not a channel link
            if not any(x in word.lower() for x in ['t.me/', 'telegram.me/', '@']):
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
        lines = message.caption.split('\n')
        title = lines[0].strip()
        
        # Remove URLs from title
        words = title.split()
        clean_words = [w for w in words if not w.startswith('http')]
        title = ' '.join(clean_words)
        
        # Remove common file indicators
        title = title.replace('📄', '').replace('**', '').strip()
        
        # Limit to 100 characters
        if len(title) > 100:
            title = title[:97] + "..."
        
        return title if title else "Adult Video"
    
    # Fallback to filename if available
    if message.video and message.video.file_name:
        filename = message.video.file_name
        # Remove extension
        title = os.path.splitext(filename)[0]
        return title[:100]
    
    if message.document and message.document.file_name:
        filename = message.document.file_name
        title = os.path.splitext(filename)[0]
        return title[:100]
    
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
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                print(f"🗑️ Cleaned up: {file_path}")
            except Exception as e:
                print(f"⚠️ Cleanup failed for {file_path}: {e}")

def get_file_size_mb(file_path):
    """
    Get file size in MB
    
    Args:
        file_path: Path to file
        
    Returns:
        Formatted file size string
    """
    if os.path.exists(file_path):
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        return f"{size_mb:.2f} MB"
    return "Unknown"

def get_file_size_bytes(file_path):
    """
    Get file size in bytes
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes or 0 if error
    """
    if os.path.exists(file_path):
        return os.path.getsize(file_path)
    return 0

# ============================================
# VIDEO INFO
# ============================================

def get_video_duration(video_path):
    """
    Get video duration using FFmpeg
    
    Args:
        video_path: Path to video file
        
    Returns:
        Duration in seconds or None
    """
    try:
        cmd = [
            FFMPEG_PATH,
            '-i', video_path,
            '-hide_banner'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        # Parse duration from stderr
        import re
        duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})', result.stderr)
        
        if duration_match:
            hours = int(duration_match.group(1))
            minutes = int(duration_match.group(2))
            seconds = int(duration_match.group(3))
            
            total_seconds = hours * 3600 + minutes * 60 + seconds
            return total_seconds
        
        return None
        
    except Exception as e:
        print(f"⚠️ Duration check failed: {e}")
        return None

def format_duration(seconds):
    """
    Format duration in seconds to HH:MM:SS
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if not seconds:
        return "Unknown"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"
        
