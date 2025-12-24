"""
Database operations - MongoDB optional with fallback
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
from config import MONGODB_URI, DATABASE_NAME, DEFAULT_POSTING_INTERVAL
import sys

# Try MongoDB connection
USING_MONGODB = False
try:
    print("Attempting MongoDB connection...")
    mongo_client = MongoClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000
    )
    # Test connection
    mongo_client.admin.command('ping')
    db = mongo_client[DATABASE_NAME]
    USING_MONGODB = True
    print("✅ MongoDB connected successfully")
    
except Exception as e:
    print(f"⚠️ MongoDB connection failed: {e}")
    print("⚠️ Falling back to in-memory storage")
    print("⚠️ Note: All data will be lost on restart!")
    
    # In-memory database fallback
    class InMemoryCollection:
        def __init__(self):
            self.data = []
            self.id_counter = 0
            
        def insert_one(self, document):
            document['_id'] = self.id_counter
            self.id_counter += 1
            self.data.append(document.copy())
            return type('InsertResult', (), {'inserted_id': document['_id']})()
            
        def find_one(self, query=None, **kwargs):
            if query is None:
                query = {}
            
            for doc in self.data:
                match = True
                for key, value in query.items():
                    if key == '_id':
                        if doc.get('_id') != value:
                            match = False
                            break
                    elif isinstance(value, dict):
                        # Handle complex queries like {"$ne": True}
                        if "$ne" in value:
                            if doc.get(key) == value["$ne"]:
                                match = False
                                break
                        elif "$gte" in value:
                            if not (doc.get(key) and doc.get(key) >= value["$gte"]):
                                match = False
                                break
                    else:
                        if doc.get(key) != value:
                            match = False
                            break
                if match:
                    return doc.copy()
            return None
            
        def update_one(self, query, update, upsert=False):
            for doc in self.data:
                match = True
                for key, value in query.items():
                    if doc.get(key) != value:
                        match = False
                        break
                if match:
                    if "$set" in update:
                        doc.update(update["$set"])
                    return
            
            # Upsert
            if upsert:
                new_doc = query.copy()
                if "$set" in update:
                    new_doc.update(update["$set"])
                self.insert_one(new_doc)
                
        def count_documents(self, query):
            count = 0
            for doc in self.data:
                match = True
                for key, value in query.items():
                    if isinstance(value, dict):
                        if "$ne" in value:
                            if doc.get(key) == value["$ne"]:
                                match = False
                                break
                        elif "$gte" in value:
                            if not (doc.get(key) and doc.get(key) >= value["$gte"]):
                                match = False
                                break
                    else:
                        if doc.get(key) != value:
                            match = False
                            break
                if match:
                    count += 1
            return count
            
        def find(self, query, **kwargs):
            results = []
            for doc in self.data:
                match = True
                for key, value in query.items():
                    if isinstance(value, dict):
                        if "$ne" in value:
                            if doc.get(key) == value["$ne"]:
                                match = False
                                break
                        elif "$gte" in value:
                            if not (doc.get(key) and doc.get(key) >= value["$gte"]):
                                match = False
                                break
                    else:
                        if doc.get(key) != value:
                            match = False
                            break
                if match:
                    results.append(doc.copy())
            
            # Handle sorting
            sort = kwargs.get('sort')
            if sort:
                field, order = sort[0]
                results.sort(key=lambda x: x.get(field, ''), reverse=(order == -1))
            
            # Return cursor-like object
            class Cursor:
                def __init__(self, data):
                    self._data = data
                    
                def limit(self, n):
                    return self._data[:n]
                    
            return Cursor(results)
    
    # Create in-memory collections
    class InMemoryDB:
        def __init__(self):
            self.queue = InMemoryCollection()
            self.posted = InMemoryCollection()
            self.statistics = InMemoryCollection()
            self.config = InMemoryCollection()
            # Set default posting interval
            self.config.insert_one({
                "setting": "posting_interval",
                "minutes": DEFAULT_POSTING_INTERVAL
            })
    
    db = InMemoryDB()

# Collections
if USING_MONGODB:
    video_queue = db.queue
    posted_videos = db.posted
    statistics = db.statistics
    bot_config = db.config
else:
    video_queue = db.queue
    posted_videos = db.posted
    statistics = db.statistics
    bot_config = db.config

# ============================================
# CONFIG OPERATIONS
# ============================================

def get_posting_interval():
    """Get current posting interval from database"""
    try:
        config = bot_config.find_one({"setting": "posting_interval"})
        if config:
            return config['minutes']
    except:
        pass
    return DEFAULT_POSTING_INTERVAL

def set_posting_interval(minutes):
    """Set new posting interval"""
    try:
        bot_config.update_one(
            {"setting": "posting_interval"},
            {"$set": {"minutes": minutes, "updated_at": datetime.now()}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error setting interval: {e}")
        return False

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
    try:
        statistics.insert_one({
            "action": action,
            "details": details,
            "timestamp": datetime.now()
        })
    except Exception as e:
        print(f"Stats update error: {e}")

def get_statistics():
    """Get comprehensive statistics"""
    try:
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
    except Exception as e:
        print(f"Stats error: {e}")
        return {
            "total": {"found": 0, "posted": 0, "pending": 0},
            "today": {"found": 0, "posted": 0},
            "week": {"found": 0, "posted": 0},
            "last_posted": None,
            "next_video": None,
            "posting_rate": {
                "interval_minutes": DEFAULT_POSTING_INTERVAL,
                "videos_per_hour": 10,
                "hours_to_clear": 0
            }
        }

def get_queue_list(limit=10):
    """Get list of pending videos"""
    try:
        return list(video_queue.find({"posted": False}).limit(limit))
    except:
        return []
                    
