from pyrogram import Client, filters
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("test_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message()
async def test_all_messages(client, message):
    """Catch ALL messages"""
    print(f"\n{'='*50}")
    print(f"Message received from: {message.chat.title if message.chat else 'Unknown'}")
    print(f"Chat ID: {message.chat.id if message.chat else 'Unknown'}")
    print(f"Message Type: {message.media if message.media else 'text'}")
    print(f"{'='*50}\n")

print("Test bot started - will show ALL messages received")
app.run()
