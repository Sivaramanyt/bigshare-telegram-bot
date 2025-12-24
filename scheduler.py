"""
Video posting scheduler
"""

import schedule
import time
from threading import Thread
from pyrogram import Client
from config import MAIN_CHANNEL
from database import get_next_video, mark_as_posted, get_pending_count, get_posting_interval, update_statistics
from captions import get_active_caption

app_instance = None

def set_app_instance(app):
    """Set the Pyrogram app instance"""
    global app_instance
    app_instance = app

def post_from_queue():
    """Post one video from queue to main channel"""
    
    video = get_next_video()
    
    if not video:
        print("📭 Queue is empty, nothing to post")
        return
    
    try:
        print(f"\n{'='*50}")
        print(f"📤 POSTING TO MAIN CHANNEL")
        print(f"{'='*50}")
        print(f"Title: {video['title']}")
        print(f"Link: {video['bigshare_link']}")
        
        # Generate caption
        caption = get_active_caption(video['title'], video['bigshare_link'])
        
        # Post to channel
        with app_instance:
            if video.get('thumbnail_file_id'):
                print("🖼️ Posting with thumbnail...")
                app_instance.send_photo(
                    chat_id=MAIN_CHANNEL,
                    photo=video['thumbnail_file_id'],
                    caption=caption
                )
            else:
                print("📝 Posting text only...")
                app_instance.send_message(
                    chat_id=MAIN_CHANNEL,
                    text=caption
                )
        
        # Mark as posted
        mark_as_posted(video['_id'])
        update_statistics("video_posted", {"title": video['title']})
        
        remaining = get_pending_count()
        print(f"✅ Posted successfully!")
        print(f"📊 Remaining in queue: {remaining}")
        print(f"{'='*50}\n")
        
    except Exception as e:
        print(f"❌ Posting error: {e}")
        update_statistics("post_error", {"error": str(e), "video_id": str(video['_id'])})

def schedule_posts():
    """Main scheduler loop"""
    
    interval = get_posting_interval()
    schedule.every(interval).minutes.do(post_from_queue)
    
    videos_per_hour = 60 / interval
    print(f"\n⏰ SCHEDULER STARTED")
    print(f"{'='*50}")
    print(f"Interval: {interval} minutes")
    print(f"Rate: {videos_per_hour:.1f} videos/hour")
    print(f"{'='*50}\n")
    
    while True:
        schedule.run_pending()
        time.sleep(30)  # Check every 30 seconds

def run_scheduler():
    """Run scheduler in separate thread"""
    scheduler_thread = Thread(target=schedule_posts, daemon=True)
    scheduler_thread.start()
    print("✅ Scheduler thread started")
