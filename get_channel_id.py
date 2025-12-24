from pyrogram import Client
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("test_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

with app:
    # Get file store channel info
    # Replace with your channel username or invite link
    try:
        chat = app.get_chat("@your_file_store_channel")  # or use channel ID
        print(f"Channel Name: {chat.title}")
        print(f"Channel ID: {chat.id}")
        print(f"Channel Type: {chat.type}")
    except Exception as e:
        print(f"Error: {e}")
