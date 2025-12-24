"""
Database operations using MongoDB
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
from config import MONGODB_URI, DATABASE_NAME

# MongoDB connection
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client[DATABASE_NAME]

# Collections
video_queue = db.queue
posted_videos = db.posted
statistics = db.statistics
bot_config = db.config

# ============================================
# CONFIG OPERATIONS
# ============================================

def get_posting_interval():
    """Get current posting interval from database"""
    config = bot_config.find_one({"setting": "posting_interval"})
    if config:
        return config['minutes']
    return 6  # Default

def set_posting_interval(minutes):
    """Set new posting interval"""
    bot_config.update_one(
        {"setting": "posting_interval"},
        {"$set": {"minutes": minutes, "updated_at": datetime.now()}},
        upsert=True
    )
    return True

# ============================================
# QUEUE OPERATIONS
# ============================================

def add_to_queue(video_data):
    """Add video to queue"""
    video_data['added_at'] = datetime.now()
    video_data['posted'] = False
    result = video_queue.insert_one(video_data)
    return result.inserted_id

def get_next_video():
    """Get next video from queue"""
    return video_queue.find_one({"posted": False})

def mark_as_posted(video_id):
    """Mark video as posted"""
    video_queue.update_one(
        {"_id": video_id},
        {"$set": {"posted": True, "posted_at": datetime.now()}}
    )

def get_pending_count():
    """Get count of pending videos"""
    return video_queue.count_documents({"posted": False})

def check_duplicate(message_id):
    """Check if video already in queue"""
    return video_queue.find_one({"message_id": message_id}) is not None

# ============================================
# STATISTICS OPERATIONS
# ============================================

def update_statistics(action, details={}):
    """Update statistics"""
    statistics.insert_one({
        "action": action,
        "details": details,
        "timestamp": datetime.now()
    })

def get_statistics():
    """Get comprehensive statistics"""
    total_found = video_queue.count_documents({})
    total_posted = video_queue.count_documents({"posted": True})
    total_pending = video_queue.count_documents({"posted": False})
    
    today_start = datetime.now().replace(hour=0, minute=0, second=0)
    today_found = video_queue.count_documents({"added_at": {"$gte": today_start}})
    today_posted = video_queue.count_documents({
        "posted": True,
        "posted_at": {"$gte": today_start}
    })
    
    week_start = datetime.now() - timedelta(days=7)
    week_found = video_queue.count_documents({"added_at": {"$gte": week_start}})
    week_posted = video_queue.count_documents({
        "posted": True,
        "posted_at": {"$gte": week_start}
    })
    
    last_posted = video_queue.find_one(
        {"posted": True},
        sort=[("posted_at", -1)]
    )
    
    next_video = video_queue.find_one({"posted": False})
    
    interval = get_posting_interval()
    videos_per_hour = 60 / interval
    
    if total_pending > 0:
        hours_to_clear = total_pending / videos_per_hour
    else:
        hours_to_clear = 0
    
    return {
        "total": {
            "found": total_found,
            "posted": total_posted,
            "pending": total_pending
        },
        "today": {
            "found": today_found,
            "posted": today_posted
        },
        "week": {
            "found": week_found,
            "posted": week_posted
        },
        "last_posted": last_posted,
        "next_video": next_video,
        "posting_rate": {
            "interval_minutes": interval,
            "videos_per_hour": videos_per_hour,
            "hours_to_clear": hours_to_clear
        }
    }

def get_queue_list(limit=10):
    """Get list of pending videos"""
    return list(video_queue.find({"posted": False}).limit(limit))
