"""
Admin commands for bot control
"""

from pyrogram import Client, filters
from config import ADMIN_USER_ID
from database import (
    get_statistics,
    get_queue_list,
    get_posting_interval,
    set_posting_interval,
    get_pending_count
)
from scheduler import post_from_queue

def setup_admin_commands(app):
    """Setup all admin commands"""
    
    @app.on_message(filters.command("start") & filters.user(ADMIN_USER_ID))
    async def start_command(client, message):
        """Welcome message"""
        await message.reply(
            "🤖 **BigShare Automation Bot**\n\n"
            "✅ Bot is running!\n\n"
            "Use /help to see all commands."
        )
    
    @app.on_message(filters.command("stats") & filters.user(ADMIN_USER_ID))
    async def show_statistics(client, message):
        """Show detailed statistics"""
        
        stats = get_statistics()
        
        stats_text = f"""📊 **Video Statistics Dashboard**

━━━━━━━━━━━━━━━━━━━━
📦 **Overall Stats**
━━━━━━━━━━━━━━━━━━━━
📥 Total Found: **{stats['total']['found']}** videos
✅ Total Posted: **{stats['total']['posted']}** videos
⏳ Pending: **{stats['total']['pending']}** videos

━━━━━━━━━━━━━━━━━━━━
📅 **Today's Activity**
━━━━━━━━━━━━━━━━━━━━
📥 Found: **{stats['today']['found']}** videos
✅ Posted: **{stats['today']['posted']}** videos

━━━━━━━━━━━━━━━━━━━━
📈 **This Week (7 days)**
━━━━━━━━━━━━━━━━━━━━
📥 Found: **{stats['week']['found']}** videos
✅ Posted: **{stats['week']['posted']}** videos

━━━━━━━━━━━━━━━━━━━━
⚙️ **Posting Configuration**
━━━━━━━━━━━━━━━━━━━━
⏱️ Interval: **{stats['posting_rate']['interval_minutes']}** minutes
📊 Rate: **{stats['posting_rate']['videos_per_hour']:.1f}** videos/hour
⏰ Time to clear queue: **{stats['posting_rate']['hours_to_clear']:.1f}** hours

━━━━━━━━━━━━━━━━━━━━
"""
        
        if stats['last_posted']:
            last_time = stats['last_posted'].get('posted_at')
            if last_time:
                stats_text += f"\n🕐 Last Posted: {last_time.strftime('%I:%M %p, %d %b')}"
        
        if stats['next_video']:
            stats_text += f"\n⏭️ Next: **{stats['next_video']['title'][:50]}...**"
        
        await message.reply(stats_text)
    
    @app.on_message(filters.command("interval") & filters.user(ADMIN_USER_ID))
    async def change_interval(client, message):
        """Change posting interval"""
        
        try:
            parts = message.text.split()
            if len(parts) < 2:
                await message.reply(
                    "❌ **Usage:** `/interval <minutes>`\n\n"
                    "**Popular presets:**\n"
                    "• `/interval 3` - 20 videos/hour (very active)\n"
                    "• `/interval 5` - 12 videos/hour (active)\n"
                    "• `/interval 6` - 10 videos/hour (default)\n"
                    "• `/interval 8` - 7.5 videos/hour\n"
                    "• `/interval 10` - 6 videos/hour\n"
                    "• `/interval 15` - 4 videos/hour\n"
                    "• `/interval 20` - 3 videos/hour\n"
                    "• `/interval 30` - 2 videos/hour (slow)"
                )
                return
            
            minutes = int(parts[1])
            
            if minutes < 1 or minutes > 60:
                await message.reply("❌ Interval must be between 1-60 minutes")
                return
            
            set_posting_interval(minutes)
            videos_per_hour = 60 / minutes
            
            await message.reply(
                f"✅ **Posting interval updated!**\n\n"
                f"⏱️ New interval: **{minutes}** minutes\n"
                f"📊 New rate: **{videos_per_hour:.1f}** videos/hour\n\n"
                f"⚠️ **Note:** Restart bot for changes to take effect"
            )
            
        except ValueError:
            await message.reply("❌ Invalid number. Example: `/interval 8`")
    
    @app.on_message(filters.command("post_now") & filters.user(ADMIN_USER_ID))
    async def force_post(client, message):
        """Force post next video immediately"""
        
        if get_pending_count() == 0:
            await message.reply("❌ Queue is empty!")
            return
        
        await message.reply("⏳ Posting next video...")
        post_from_queue()
        await message.reply("✅ Posted next video from queue!")
    
    @app.on_message(filters.command("queue") & filters.user(ADMIN_USER_ID))
    async def show_queue(client, message):
        """Show next videos in queue"""
        
        videos = get_queue_list(limit=10)
        
        if not videos:
            await message.reply("📭 Queue is empty!")
            return
        
        queue_text = "📋 **Next 10 Videos in Queue:**\n\n"
        
        for i, video in enumerate(videos, 1):
            added_time = video['added_at'].strftime('%I:%M %p')
            queue_text += f"{i}. {video['title'][:40]}...\n   ⏰ Added: {added_time}\n\n"
        
        total_pending = get_pending_count()
        queue_text += f"\n📊 Total pending: **{total_pending}** videos"
        
        await message.reply(queue_text)
    
    @app.on_message(filters.command("help") & filters.user(ADMIN_USER_ID))
    async def show_help(client, message):
        """Show all admin commands"""
        
        help_text = """🤖 **Admin Commands**

📊 **Statistics:**
`/stats` - Full statistics dashboard
`/queue` - Show next 10 videos in queue

⚙️ **Configuration:**
`/interval <minutes>` - Change posting interval

**Examples:**
• `/interval 6` - 10 videos/hour (default)
• `/interval 8` - 7.5 videos/hour
• `/interval 10` - 6 videos/hour
• `/interval 20` - 3 videos/hour

🎬 **Manual Control:**
`/post_now` - Post next video immediately

❓ **Help:**
`/help` - Show this message
`/start` - Bot status

━━━━━━━━━━━━━━━━━━━━
💡 **Tips:**
• Upload videos to file store channel
• Bot automatically processes and queues
• Videos post at scheduled intervals
• Check /stats for queue status
"""
        
        await message.reply(help_text)
    
    print("✅ Admin commands setup complete")
