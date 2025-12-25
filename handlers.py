"""
Message handlers for Telegram bot
StreamFlash.sx integration
"""

from pyrogram import Client, filters
from config import FILE_STORE_CHANNEL, ADMIN_USER_ID, BOT_TOKEN
from database import add_to_queue, check_duplicate, get_pending_count, update_statistics
from utils import (
    upload_to_streamflash,
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

async def get_telegram_file_url(client, message):
    """
    Get direct Telegram CDN URL for video file
    This URL can be used by StreamFlash to download the video
    
    Args:
        client: Pyrogram client
        message: Message with video/document
        
    Returns:
        Telegram file URL or None
    """
    try:
        # Get file ID
        if message.video:
            file_id = message.video.file_id
        elif message.document:
            file_id = message.document.file_id
        else:
            return None
        
        # Get file path from Telegram
        file = await client.get_file(file_id)
        
        # Construct Telegram CDN URL
        # Format: https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}
        telegram_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        print(f"   Telegram CDN URL: {telegram_url[:80]}...")
        return telegram_url
        
    except Exception as e:
        print(f"❌ Error getting Telegram URL: {e}")
        return None

def setup_handlers(app):
    """Setup all message handlers"""
    
    @app.on_message(filters.chat(FILE_STORE_CHANNEL) & (filters.video | filters.document))
    async def handle_new_video(client, message):
        """Handle new videos in file store channel"""
        
        print(f"\n{'='*50}")
        print(f"📥 NEW VIDEO DETECTED")
        print(f"{'='*50}")
        print(f"Chat: {message.chat.title if message.chat else 'Unknown'}")
        print(f"Message ID: {message.id}")
        
        # Check for duplicates
        if check_duplicate(message.id):
            print("⚠️ Video already in queue, skipping...")
            return
        
        # Extract title
        video_title = extract_video_title(message)
        print(f"📝 Title: {video_title}")
        
        video_path = None
        streamflash_link = None
        thumbnail_path = None
        thumb_file_id = None
        upload_method = "unknown"
        
        try:
            # Check for direct download link in caption
            direct_link = extract_direct_link(message)
            
            if direct_link:
                print(f"🔗 Direct link detected: {direct_link}")
                upload_method = "remote_url"
                
                # Upload to StreamFlash using the URL
                streamflash_link = upload_to_streamflash(video_url=direct_link)
                
                # Download for thumbnail extraction
                video_path = await download_telegram_video(message, f"temp_downloads/video_{message.id}.mp4")
                
            else:
                print(f"📥 Downloading video from Telegram...")
                upload_method = "telegram_file"
                
                # Download video file first
                video_path = await download_telegram_video(message, f"temp_downloads/video_{message.id}.mp4")
                
                if not video_path:
                    print("❌ Video download failed!")
                    return
                
                file_size = get_file_size_mb(video_path)
                print(f"📦 File size: {file_size}")
                
                # Get Telegram file URL for StreamFlash
                print(f"🔗 Getting Telegram file URL...")
                telegram_url = await get_telegram_file_url(client, message)
                
                if not telegram_url:
                    print("❌ Failed to get Telegram URL!")
                    # Notify admin
                    try:
                        await client.send_message(
                            ADMIN_USER_ID,
                            f"❌ Failed to get Telegram URL\n\n{video_title}"
                        )
                    except:
                        pass
                    return
                
                # Upload to StreamFlash using Telegram URL
                streamflash_link = upload_to_streamflash(video_url=telegram_url)
            
            # Check if upload succeeded
            if not streamflash_link:
                print("❌ StreamFlash upload failed!")
                update_statistics("upload_failed", {"message_id": message.id, "title": video_title})
                
                # Notify admin
                try:
                    await client.send_message(
                        ADMIN_USER_ID,
                        f"❌ StreamFlash Upload Failed!\n\n"
                        f"Video: {video_title}\n"
                        f"Message ID: {message.id}\n\n"
                        f"Please check:\n"
                        f"• StreamFlash API key\n"
                        f"• Server status\n"
                        f"• Video URL accessibility"
                    )
                except:
                    pass
                
                return
            
            print(f"✅ StreamFlash Link: {streamflash_link}")
            
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
                "streamflash_link": streamflash_link,  # Changed from bigshare_link
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
                    f"❌ Processing Error!\n\n"
                    f"Video: {video_title}\n"
                    f"Error: {str(e)[:200]}\n\n"
                    f"Check logs for details."
                )
            except:
                pass
        
        finally:
            # Cleanup temporary files
            cleanup_temp_files(video_path, thumbnail_path)
    
    # Test channel access command
    @app.on_message(filters.command("test") & filters.user(ADMIN_USER_ID))
    async def test_channel_access(client, message):
        """Test if bot can access file store channel"""
        try:
            chat = await client.get_chat(FILE_STORE_CHANNEL)
            
            # Try to get recent messages
            try:
                messages = []
                async for msg in client.get_chat_history(FILE_STORE_CHANNEL, limit=5):
                    msg_type = "video" if msg.video else "document" if msg.document else "other"
                    messages.append(f"• ID {msg.id}: {msg_type}")
                
                recent_msgs = "\n".join(messages) if messages else "No messages found"
            except:
                recent_msgs = "Cannot read message history"
            
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
                f"❌ **Cannot Access File Store Channel!**\n\n"
                f"**Error:** `{e}`\n\n"
                f"**Configured ID:** `{FILE_STORE_CHANNEL}`\n\n"
                f"**Troubleshooting:**\n"
                f"• Ensure bot is added to channel\n"
                f"• Ensure bot has admin rights\n"
                f"• Check channel ID is correct\n"
                f"• Verify channel ID starts with -100"
            )
    
    # Debug configuration command
    @app.on_message(filters.command("debug") & filters.user(ADMIN_USER_ID))
    async def debug_config(client, message):
        """Show current configuration"""
        from config import MAIN_CHANNEL, STREAMFLASH_API_KEY
        
        await message.reply(
            f"🔧 **Bot Configuration**\n\n"
            f"**Channels:**\n"
            f"File Store: `{FILE_STORE_CHANNEL}`\n"
            f"Main Channel: `{MAIN_CHANNEL}`\n\n"
            f"**Admin:**\n"
            f"Your ID: `{message.from_user.id}`\n"
            f"Configured Admin: `{ADMIN_USER_ID}`\n"
            f"Match: {'✅ Yes' if message.from_user.id == ADMIN_USER_ID else '❌ No'}\n\n"
            f"**StreamFlash:**\n"
            f"API Key: `{STREAMFLASH_API_KEY[:20]}...`\n\n"
            f"**Bot Status:**\n"
            f"Running: ✅ Active\n"
            f"Handlers: ✅ Loaded"
        )
    
    # Test StreamFlash API
    @app.on_message(filters.command("testapi") & filters.user(ADMIN_USER_ID))
    async def test_streamflash_api(client, message):
        """Test StreamFlash API with a sample video"""
        await message.reply("🧪 Testing StreamFlash API...\n\nPlease wait...")
        
        # Use a small public test video
        test_url = "https://sample-videos.com/video321/mp4/240/big_buck_bunny_240p_1mb.mp4"
        
        try:
            streamflash_link = upload_to_streamflash(video_url=test_url)
            
            if streamflash_link:
                await message.reply(
                    f"✅ **StreamFlash API Test Successful!**\n\n"
                    f"Test Video URL: {test_url}\n\n"
                    f"StreamFlash Link: {streamflash_link}\n\n"
                    f"API is working correctly!"
                )
            else:
                await message.reply(
                    f"❌ **StreamFlash API Test Failed!**\n\n"
                    f"Upload returned no link.\n\n"
                    f"Check logs for details."
                )
        except Exception as e:
            await message.reply(
                f"❌ **StreamFlash API Test Error!**\n\n"
                f"Error: `{e}`\n\n"
                f"Check:\n"
                f"• API key is correct\n"
                f"• StreamFlash service is online\n"
                f"• Network connectivity"
            )
    
    # Get channel ID from forwarded message
    @app.on_message(filters.forwarded & filters.private & filters.user(ADMIN_USER_ID))
    async def check_forwarded(client, message):
        """Check forwarded message details to get channel ID"""
        if message.forward_from_chat:
            await message.reply(
                f"📨 **Forwarded Message Info**\n\n"
                f"**Channel:**\n"
                f"Title: {message.forward_from_chat.title}\n"
                f"ID: `{message.forward_from_chat.id}`\n"
                f"Type: {message.forward_from_chat.type}\n\n"
                f"**Use this in .env:**\n"
                f"`FILE_STORE_CHANNEL={message.forward_from_chat.id}`\n"
                f"or\n"
                f"`MAIN_CHANNEL={message.forward_from_chat.id}`"
            )
    
    print("✅ Handlers setup complete")
    print(f"✅ Monitoring channel ID: {FILE_STORE_CHANNEL}")
        
