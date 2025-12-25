"""
Message handlers for Telegram bot
StreamFlash.sx integration with corrected Telegram URL method
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
            file_id = file.file_id
        elif message.document:
            file = message.document
            file_id = file.file_id
        else:
            print("❌ No video or document in message")
            return None
        
        print(f"   File ID: {file_id[:50]}...")
        
        # Download media to get file info
        # We need to use Telegram Bot API to get file_path
        import requests
        
        # Get file path using Bot API
        api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile"
        response = requests.get(api_url, params={"file_id": file_id}, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("ok"):
                file_path = data["result"]["file_path"]
                
                # Construct direct download URL
                telegram_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                
                print(f"   ✅ Telegram URL obtained")
                print(f"   Path: {file_path}")
                return telegram_url
            else:
                print(f"❌ Telegram API error: {data}")
                return None
        else:
            print(f"❌ Failed to get file info: Status {response.status_code}")
            return None
        
    except Exception as e:
        print(f"❌ Error getting Telegram URL: {e}")
        import traceback
        traceback.print_exc()
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
        print(f"Chat ID: {message.chat.id}")
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
                print(f"📥 Telegram file detected, processing...")
                upload_method = "telegram_file"
                
                # Get Telegram file URL for StreamFlash
                print(f"🔗 Getting Telegram file URL...")
                telegram_url = await get_telegram_file_url(client, message)
                
                if not telegram_url:
                    print("❌ Failed to get Telegram URL!")
                    
                    # Notify admin
                    try:
                        await client.send_message(
                            ADMIN_USER_ID,
                            f"❌ Failed to get Telegram URL\n\n"
                            f"Video: {video_title}\n"
                            f"Message ID: {message.id}\n\n"
                            f"Possible reasons:\n"
                            f"• File too large (>20MB limit for Bot API)\n"
                            f"• Temporary API issue\n"
                            f"• Invalid file format"
                        )
                    except:
                        pass
                    return
                
                # Upload to StreamFlash using Telegram URL
                print(f"📤 Uploading to StreamFlash via Telegram URL...")
                streamflash_link = upload_to_streamflash(video_url=telegram_url)
                
                # Download for thumbnail extraction
                print(f"📥 Downloading for thumbnail...")
                video_path = await download_telegram_video(message, f"temp_downloads/video_{message.id}.mp4")
            
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
                        f"Check:\n"
                        f"• StreamFlash API key valid\n"
                        f"• Video URL accessible\n"
                        f"• StreamFlash service online"
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
                    # Upload thumbnail to file store
                    try:
                        thumb_msg = await client.send_photo(
                            FILE_STORE_CHANNEL,
                            thumbnail_path,
                            caption=f"🖼️ Thumbnail for message {message.id}"
                        )
                        thumb_file_id = thumb_msg.photo.file_id
                        print(f"✅ Thumbnail uploaded")
                    except Exception as e:
                        print(f"⚠️ Thumbnail upload failed: {e}")
            else:
                print("⚠️ No video file for thumbnail extraction")
            
            # Add to queue
            video_data = {
                "message_id": message.id,
                "title": video_title,
                "streamflash_link": streamflash_link,
                "thumbnail_file_id": thumb_file_id,
                "upload_method": upload_method
            }
            
            add_to_queue(video_data)
            update_statistics("video_found", {"title": video_title, "method": upload_method})
            
            queue_count = get_pending_count()
            print(f"✅ Added to queue! Total pending: {queue_count}")
            print(f"{'='*50}\n")
            
            # Notify admin of success
            try:
                notification = get_admin_notification(video_title, queue_count)
                await client.send_message(ADMIN_USER_ID, notification)
            except Exception as e:
                print(f"⚠️ Admin notification failed: {e}")
            
        except Exception as e:
            print(f"❌ FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            update_statistics("processing_error", {"error": str(e), "message_id": message.id})
            
            # Notify admin of error
            try:
                await client.send_message(
                    ADMIN_USER_ID,
                    f"❌ Processing Error!\n\n"
                    f"Video: {video_title}\n"
                    f"Message ID: {message.id}\n"
                    f"Error: {str(e)[:300]}\n\n"
                    f"Check Koyeb logs for full traceback."
                )
            except:
                pass
        
        finally:
            # Cleanup temporary files
            cleanup_temp_files(video_path, thumbnail_path)
    
    # Test channel access
    @app.on_message(filters.command("test") & filters.user(ADMIN_USER_ID))
    async def test_channel_access(client, message):
        """Test file store channel access"""
        try:
            chat = await client.get_chat(FILE_STORE_CHANNEL)
            
            # Get recent messages
            try:
                messages = []
                count = 0
                async for msg in client.get_chat_history(FILE_STORE_CHANNEL, limit=5):
                    count += 1
                    msg_type = "video" if msg.video else "document" if msg.document else "text"
                    messages.append(f"• ID {msg.id}: {msg_type}")
                
                recent_msgs = "\n".join(messages) if messages else "No messages"
            except Exception as e:
                recent_msgs = f"Cannot read: {e}"
            
            await message.reply(
                f"✅ **Channel Access Test**\n\n"
                f"**Channel Info:**\n"
                f"Title: {chat.title}\n"
                f"ID: `{chat.id}`\n"
                f"Type: {chat.type}\n\n"
                f"**Recent Messages:**\n{recent_msgs}\n\n"
                f"**Configuration:**\n"
                f"Configured: `{FILE_STORE_CHANNEL}`\n"
                f"Match: {'✅' if chat.id == FILE_STORE_CHANNEL else '❌'}"
            )
        except Exception as e:
            await message.reply(
                f"❌ **Channel Access Failed**\n\n"
                f"Error: `{e}`\n\n"
                f"Configured ID: `{FILE_STORE_CHANNEL}`"
            )
    
    # Debug configuration
    @app.on_message(filters.command("debug") & filters.user(ADMIN_USER_ID))
    async def debug_config(client, message):
        """Show bot configuration"""
        from config import MAIN_CHANNEL, STREAMFLASH_API_KEY
        
        await message.reply(
            f"🔧 **Bot Configuration**\n\n"
            f"**Channels:**\n"
            f"File Store: `{FILE_STORE_CHANNEL}`\n"
            f"Main: `{MAIN_CHANNEL}`\n\n"
            f"**Admin:**\n"
            f"You: `{message.from_user.id}`\n"
            f"Config: `{ADMIN_USER_ID}`\n"
            f"Match: {'✅' if message.from_user.id == ADMIN_USER_ID else '❌'}\n\n"
            f"**StreamFlash:**\n"
            f"Key: `{STREAMFLASH_API_KEY[:20]}...`\n\n"
            f"**Status:**\n"
            f"Running: ✅ Active\n"
            f"Handlers: ✅ Loaded"
        )
    
    # Test StreamFlash API
    @app.on_message(filters.command("testapi") & filters.user(ADMIN_USER_ID))
    async def test_streamflash_api(client, message):
        """Test StreamFlash API"""
        await message.reply("🧪 Testing StreamFlash API...\n\nPlease wait...")
        
        # Small public test video
        test_url = "https://sample-videos.com/video321/mp4/240/big_buck_bunny_240p_1mb.mp4"
        
        try:
            print(f"\n{'='*50}")
            print(f"🧪 API TEST STARTED")
            print(f"{'='*50}")
            
            streamflash_link = upload_to_streamflash(video_url=test_url)
            
            print(f"{'='*50}")
            print(f"🧪 API TEST COMPLETED")
            print(f"{'='*50}\n")
            
            if streamflash_link:
                await message.reply(
                    f"✅ **API Test Successful!**\n\n"
                    f"Test URL: {test_url}\n\n"
                    f"StreamFlash Link:\n{streamflash_link}\n\n"
                    f"✅ API is working!"
                )
            else:
                await message.reply(
                    f"❌ **API Test Failed**\n\n"
                    f"No link returned.\n\n"
                    f"Check Koyeb logs for details."
                )
        except Exception as e:
            await message.reply(
                f"❌ **API Test Error**\n\n"
                f"Error: `{e}`\n\n"
                f"Check:\n"
                f"• API key correct\n"
                f"• Service online\n"
                f"• Network OK"
            )
    
    # Get channel ID from forwarded message
    @app.on_message(filters.forwarded & filters.private & filters.user(ADMIN_USER_ID))
    async def check_forwarded(client, message):
        """Get channel ID from forwarded message"""
        if message.forward_from_chat:
            await message.reply(
                f"📨 **Channel Info**\n\n"
                f"Title: {message.forward_from_chat.title}\n"
                f"ID: `{message.forward_from_chat.id}`\n"
                f"Type: {message.forward_from_chat.type}\n\n"
                f"**Use in .env:**\n"
                f"`FILE_STORE_CHANNEL={message.forward_from_chat.id}`"
            )
    
    print("✅ Handlers setup complete")
    print(f"✅ Monitoring channel: {FILE_STORE_CHANNEL}")
        
