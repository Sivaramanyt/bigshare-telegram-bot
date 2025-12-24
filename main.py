"""
BigShare Telegram Bot - Main Entry Point
Automated video posting system with BigShare integration
"""

from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN, validate_config
from handlers import setup_handlers
from admin import setup_admin_commands
from scheduler import run_scheduler, set_app_instance
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple health check endpoint for Koyeb"""
    
    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
            <html>
            <body style="font-family: Arial; padding: 20px;">
                <h1>🤖 BigShare Telegram Bot</h1>
                <p style="color: green;">✅ Bot is running!</p>
                <p>Status: Active</p>
                <p>Health Check: OK</p>
            </body>
            </html>
            """)
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress logs
        pass

def run_health_server():
    """Run health check server for Koyeb"""
    port = int(os.getenv('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"🏥 Health check server started on port {port}")
    server.serve_forever()

def main():
    """Main function to start the bot"""
    
    print("\n" + "="*50)
    print("🤖 BIGSHARE TELEGRAM BOT")
    print("="*50)
    
    # Validate configuration
    if not validate_config():
        print("\n❌ Please configure .env file properly")
        print("Copy .env.example to .env and fill in your details")
        return
    
    print("✅ Configuration validated")
    
    # Create Pyrogram client
    app = Client(
        "bigshare_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN
    )
    
    # Set app instance for scheduler
    set_app_instance(app)
    
    # Setup handlers and commands
    setup_handlers(app)
    setup_admin_commands(app)
    
    # Start scheduler
    run_scheduler()
    
    # Start health check server in separate thread
    health_thread = Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    print("\n" + "="*50)
    print("✅ BOT STARTED SUCCESSFULLY")
    print("="*50)
    print("\n💡 Bot is now running...")
    print("📥 Monitoring file store channel for new videos")
    print("⏰ Scheduler is posting videos automatically")
    print("🏥 Health check server running")
    print("\n🛑 Press Ctrl+C to stop\n")
    
    # Run the bot
    app.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
    
