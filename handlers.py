"""
Message handlers for Telegram bot
"""

from pyrogram import Client, filters
from config import FILE_STORE_CHANNEL, ADMIN_USER_ID
from database import add_to_queue, check_duplicate, get_pending_count, update_statistics
from utils import (
    upload_to_bigshare,
    extract_thumbnail,
    extract_direct_link,
    extract_video_title,
    cleanup_temp_files,
    get_file_size_mb
)
from captions import get_admin_notification
import os

async def download_telegram_video(message, filename):
    """Download video from Telegram message"""
    try:
        file_path = await message.download(file_name=filename)
        print(f"✅ Downloaded: {file_path}")
        return file_path
    except Exception as e:
        print(f"❌ Download error: {e}")
        return None

def setup_handlers(app):
    """Setup all message handlers"""
    
    @app.on_message(filters.chat(FILE_STORE_CHANNEL) & (filters.video | filters.document))
    async def handle_new_video(client, message):
        """Handle new videos in file store channel"""
        
        print(f"\n{'='*50}")
        print(f"📥 NEW VIDEO DETECTED")
        print(f"{'='*50}")
        print(f"Message ID: {message.id}")
        
        # Check for duplicates
        if check_duplicate(message.id):
            print("⚠️ Video already in queue, skipping...")
            return
        
        # Extract title
        video_title = extract_video_title(message)
        print(f"📝 Title: {video_title}")
        
        video_path = None
        bigshare_link = None
        thumbnail_path = None
        thumb_file_id = None
        upload_method = "unknown"
        
        try:
            # Check for direct download link
            direct_link = extract_direct_link(message)
            
            if direct_link:
                print(f"🔗 Direct link detected: {direct_link}")
                upload_method = "remote_url"
                
                # Upload to BigShare via URL
                bigshare_link = upload_to_bigshare(video_url=direct_link)
                
                # Download for thumbnail extraction
                temp_filename = f"temp_downloads/video_{message.id}.mp4"
                video_path = await download_telegram_video(message, temp_filename)
                
            else:
                print(f"📥 Video file detected, downloading...")
                upload_method = "file_upload"
                
                # Download from Telegram
                temp_filename = f"temp_downloads/video_{message.id}.mp4"
                video_path = await download_telegram_video(message, temp_filename)
                
                if video_path:
                    file_size = get_file_size_mb(video_path)
                    print(f"📦 File size: {file_size}")
                    
                    # Upload to BigShare
                    bigshare_link = upload_to_bigshare(video_path=video_path)
            
            # Check if upload succeeded
            if not bigshare_link:
                print("❌ BigShare upload failed!")
                update_statistics("upload_failed", {"message_id": message.id, "title": video_title})
                return
            
            print(f"✅ BigShare Link: {bigshare_link}")
            
            # Extract thumbnail
            if video_path and os.path.exists(video_path):
                print("🖼️ Extracting thumbnail...")
                thumbnail_path = extract_thumbnail(video_path, f"thumb_{message.id}.jpg")
                
                if thumbnail_path:
                    # Upload thumbnail to file store for storage
                    thumb_msg = await client.send_photo(
                        FILE_STORE_CHANNEL,
                        thumbnail_path,
                        caption=f"🖼️ Thumbnail for message {message.id}"
                    )
                    thumb_file_id = thumb_msg.photo.file_id
                    print(f"✅ Thumbnail uploaded to file store")
            
            # Add to queue
            video_data = {
                "message_id": message.id,
                "title": video_title,
                "bigshare_link": bigshare_link,
                "thumbnail_file_id": thumb_file_id,
                "upload_method": upload_method
            }
            
            add_to_queue(video_data)
            update_statistics("video_found", {"title": video_title, "method": upload_method})
            
            queue_count = get_pending_count()
            print(f"✅ Added to queue! Total pending: {queue_count}")
            print(f"{'='*50}\n")
            
            # Notify admin
            try:
                notification = get_admin_notification(video_title, queue_count)
                await client.send_message(ADMIN_USER_ID, notification)
            except Exception as e:
                print(f"⚠️ Admin notification failed: {e}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            update_statistics("processing_error", {"error": str(e), "message_id": message.id})
        
        finally:
            # Cleanup temporary files
            cleanup_temp_files(video_path, thumbnail_path)
    
    print("✅ Handlers setup complete")
