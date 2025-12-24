"""
Message handlers for Telegram bot
Enhanced with debug logging for troubleshooting
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
    
    # Debug: Log all messages (temporary - for testing)
    @app.on_message()
    async def debug_all_messages(client, message):
        """Debug: Show all messages received by bot"""
        if message.chat:
            print(f"\n[DEBUG] Message from: {message.chat.title or 'Private'}")
            print(f"[DEBUG] Chat ID: {message.chat.id}")
            print(f"[DEBUG] Configured FILE_STORE_CHANNEL: {FILE_STORE_CHANNEL}")
            print(f"[DEBUG] Match: {message.chat.id == FILE_STORE_CHANNEL}")
            print(f"[DEBUG] Has Video: {bool(message.video)}")
            print(f"[DEBUG] Has Document: {bool(message.document)}")
            if message.video:
                print(f"[DEBUG] Video MIME: {message.video.mime_type}")
            if message.document:
                print(f"[DEBUG] Document MIME: {message.document.mime_type}")
    
    @app.on_message(filters.chat(FILE_STORE_CHANNEL) & (filters.video | filters.document))
    async def handle_new_video(client, message):
        """Handle new videos in file store channel"""
        
        print(f"\n{'='*50}")
        print(f"📥 NEW VIDEO DETECTED!")
        print(f"{'='*50}")
        print(f"Chat: {message.chat.title if message.chat else 'Unknown'}")
        print(f"Chat ID: {message.chat.id if message.chat else 'Unknown'}")
        print(f"Message ID: {message.id}")
        print(f"Has Video: {bool(message.video)}")
        print(f"Has Document: {bool(message.document)}")
        print(f"Caption: {message.caption or 'No caption'}")
        print(f"{'='*50}")
        
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
                
                # Notify admin
                try:
                    await client.send_message(
                        ADMIN_USER_ID,
                        f"❌ Upload failed!\n\n"
                        f"Video: {video_title}\n"
                        f"Message ID: {message.id}"
                    )
                except:
                    pass
                
                return
            
            print(f"✅ BigShare Link: {bigshare_link}")
            
            # Extract thumbnail
            if video_path and os.path.exists(video_path):
                print("🖼️ Extracting thumbnail...")
                thumbnail_path = extract_thumbnail(video_path, f"thumb_{message.id}.jpg")
                
                if thumbnail_path:
                    # Upload thumbnail to file store for storage
                    try:
                        thumb_msg = await client.send_photo(
                            FILE_STORE_CHANNEL,
                            thumbnail_path,
                            caption=f"🖼️ Thumbnail for message {message.id}"
                        )
                        thumb_file_id = thumb_msg.photo.file_id
                        print(f"✅ Thumbnail uploaded to file store")
                    except Exception as e:
                        print(f"⚠️ Thumbnail upload failed: {e}")
            
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
            import traceback
            traceback.print_exc()
            update_statistics("processing_error", {"error": str(e), "message_id": message.id})
            
            # Notify admin of error
            try:
                await client.send_message(
                    ADMIN_USER_ID,
                    f"❌ Processing error!\n\n"
                    f"Video: {video_title}\n"
                    f"Error: {str(e)}"
                )
            except:
                pass
        
        finally:
            # Cleanup temporary files
            cleanup_temp_files(video_path, thumbnail_path)
    
    # Test command to verify channel access
    @app.on_message(filters.command("test") & filters.user(ADMIN_USER_ID))
    async def test_channel_access(client, message):
        """Test if bot can access file store channel"""
        try:
            chat = await client.get_chat(FILE_STORE_CHANNEL)
            
            # Try to get recent messages
            try:
                messages = []
                async for msg in client.get_chat_history(FILE_STORE_CHANNEL, limit=5):
                    messages.append(f"• {msg.id}: {msg.media or 'text'}")
                
                recent_msgs = "\n".join(messages) if messages else "No messages"
            except:
                recent_msgs = "Cannot read messages"
            
            await message.reply(
                f"✅ **Channel Access Test**\n\n"
                f"**Channel Info:**\n"
                f"Title: {chat.title}\n"
                f"ID: `{chat.id}`\n"
                f"Type: {chat.type}\n\n"
                f"**Recent Messages:**\n{recent_msgs}\n\n"
                f"**Configuration:**\n"
                f"Configured ID: `{FILE_STORE_CHANNEL}`\n"
                f"Match: {'✅ Yes' if chat.id == FILE_STORE_CHANNEL else '❌ No'}"
            )
        except Exception as e:
            await message.reply(
                f"❌ **Cannot access file store channel!**\n\n"
                f"**Error:** `{e}`\n\n"
                f"**Configured ID:** `{FILE_STORE_CHANNEL}`\n\n"
                f"**Possible Issues:**\n"
                f"• Bot not added to channel\n"
                f"• Bot not admin in channel\n"
                f"• Wrong channel ID\n"
                f"• Channel is private and bot has no access"
            )
    
    # Debug command to show configuration
    @app.on_message(filters.command("debug") & filters.user(ADMIN_USER_ID))
    async def debug_config(client, message):
        """Show current configuration"""
        from config import MAIN_CHANNEL, BIGSHARE_TOKEN
        
        await message.reply(
            f"🔧 **Bot Configuration**\n\n"
            f"**Channels:**\n"
            f"File Store: `{FILE_STORE_CHANNEL}`\n"
            f"Main Channel: `{MAIN_CHANNEL}`\n\n"
            f"**Admin:**\n"
            f"Your ID: `{message.from_user.id}`\n"
            f"Configured Admin: `{ADMIN_USER_ID}`\n"
            f"Match: {'✅ Yes' if message.from_user.id == ADMIN_USER_ID else '❌ No'}\n\n"
            f"**BigShare:**\n"
            f"Token: `{BIGSHARE_TOKEN[:20]}...`\n\n"
            f"**Bot Status:**\n"
            f"Running: ✅ Yes\n"
            f"Handlers: ✅ Active"
        )
    
    # Forward test - forward any message to bot
    @app.on_message(filters.forwarded & filters.private & filters.user(ADMIN_USER_ID))
    async def check_forwarded(client, message):
        """Check forwarded message details"""
        if message.forward_from_chat:
            await message.reply(
                f"📨 **Forwarded Message Info**\n\n"
                f"**From:**\n"
                f"Title: {message.forward_from_chat.title}\n"
                f"ID: `{message.forward_from_chat.id}`\n"
                f"Type: {message.forward_from_chat.type}\n\n"
                f"**Use this ID in .env:**\n"
                f"`FILE_STORE_CHANNEL={message.forward_from_chat.id}`"
            )
    
    print("✅ Handlers setup complete")
    print(f"✅ Monitoring channel ID: {FILE_STORE_CHANNEL}")
        
