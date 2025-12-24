"""
Caption templates for video posts
Customize these templates as needed
"""

from datetime import datetime

# ============================================
# CAPTION TEMPLATES
# ============================================

def get_main_channel_caption(video_title, bigshare_link, extra_info=None):
    """
    Generate caption for main channel post
    
    Args:
        video_title: Title of the video
        bigshare_link: BigShare download link
        extra_info: Optional dict with additional info
    """
    
    caption = f"""🎬 **{video_title}**

🔗 **Watch Online / Download:**
{bigshare_link}

"""
    
    # Add extra info if provided
    if extra_info:
        if extra_info.get('duration'):
            caption += f"⏱️ Duration: {extra_info['duration']}\n"
        if extra_info.get('size'):
            caption += f"📦 Size: {extra_info['size']}\n"
        if extra_info.get('quality'):
            caption += f"📺 Quality: {extra_info['quality']}\n"
        caption += "\n"
    
    # Add footer
    caption += get_footer()
    
    return caption

def get_footer():
    """Get footer text for all posts"""
    return """⚠️ **18+ Content Only**
🔞 Adults Only - Viewer Discretion Advised

💬 Share with friends!
⭐ Stay tuned for more updates!"""

def get_custom_caption_template_1(title, link):
    """Template 1: Simple & Clean"""
    return f"""🔥 **{title}**

▶️ **WATCH NOW:**
{link}

⚠️ 18+ Only | Adults Content"""

def get_custom_caption_template_2(title, link):
    """Template 2: With emojis"""
    return f"""🎥 **{title}** 🔥

━━━━━━━━━━━━━━━━
🔗 **Download Link:**
{link}
━━━━━━━━━━━━━━━━

⚠️ 18+ Content
🔞 Adults Only
💯 HD Quality

👉 Click link to watch!"""

def get_custom_caption_template_3(title, link):
    """Template 3: Professional"""
    return f"""📹 **NEW UPLOAD**

**Title:** {title}

**Watch/Download:**
{link}

**Category:** Adult Entertainment
**Rating:** 18+
**Status:** Available Now

⚠️ Viewer discretion is advised
🔞 Must be 18+ to view"""

def get_custom_caption_template_4(title, link):
    """Template 4: Minimal"""
    return f"""🎬 {title}

🔗 {link}

18+ Only ⚠️"""

def get_custom_caption_template_5(title, link):
    """Template 5: Bollywood Style"""
    return f"""🌟 **LATEST RELEASE** 🌟

🎬 **{title}**

🔥 Watch Full Video:
{link}

✨ HD Quality Available
⚡ Fast Streaming
🎯 Direct Download

⚠️ 18+ Adult Content
🔞 Parental Guidance Required

👇 Click the link above 👆"""

# ============================================
# ACTIVE TEMPLATE SELECTION
# ============================================

# Choose which template to use (1-5 or 'main')
ACTIVE_TEMPLATE = "main"  # Options: "main", "1", "2", "3", "4", "5"

def get_active_caption(title, link, extra_info=None):
    """Get caption based on active template selection"""
    
    if ACTIVE_TEMPLATE == "1":
        return get_custom_caption_template_1(title, link)
    elif ACTIVE_TEMPLATE == "2":
        return get_custom_caption_template_2(title, link)
    elif ACTIVE_TEMPLATE == "3":
        return get_custom_caption_template_3(title, link)
    elif ACTIVE_TEMPLATE == "4":
        return get_custom_caption_template_4(title, link)
    elif ACTIVE_TEMPLATE == "5":
        return get_custom_caption_template_5(title, link)
    else:
        return get_main_channel_caption(title, link, extra_info)

# ============================================
# NOTIFICATION MESSAGES
# ============================================

def get_admin_notification(video_title, queue_count):
    """Notification when new video is added"""
    return f"""✅ **New Video Added to Queue!**

📹 **{video_title}**

📊 **Queue Status:** {queue_count} videos pending

⏰ Bot is running smoothly!"""

def get_upload_success_message(video_title):
    """Message when video is successfully uploaded to BigShare"""
    return f"✅ Successfully uploaded: {video_title}"

def get_upload_failed_message(video_title):
    """Message when upload fails"""
    return f"❌ Upload failed: {video_title}"

def get_post_success_message(video_title, remaining):
    """Message when video is posted to main channel"""
    return f"✅ Posted: {video_title}\n📊 Remaining: {remaining} videos"
