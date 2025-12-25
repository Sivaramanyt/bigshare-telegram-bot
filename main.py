"""
StreamFlash Telegram Bot - Main Entry Point
Enhanced with startup error handling
"""

import sys
import traceback

# Print Python version and environment info
print("="*60)
print("🚀 BOT STARTUP")
print("="*60)
print(f"Python Version: {sys.version}")
print(f"Platform: {sys.platform}")
print("="*60)

try:
    print("\n📦 Importing modules...")
    
    from pyrogram import Client
    print("✅ Pyrogram imported")
    
    from config import API_ID, API_HASH, BOT_TOKEN, validate_config
    print("✅ Config imported")
    
    from handlers import setup_handlers
    print("✅ Handlers imported")
    
    from admin import setup_admin_commands
    print("✅ Admin imported")
    
    from scheduler import run_scheduler, set_app_instance
    print("✅ Scheduler imported")
    
    from threading import Thread
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import os
    print("✅ Standard libraries imported")
    
    print("\n✅ All imports successful!\n")

except ImportError as e:
    print(f"\n❌ IMPORT ERROR!")
    print(f"Error: {e}")
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR DURING IMPORT!")
    print(f"Error: {e}")
    traceback.print_exc()
    sys.exit(1)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple health check endpoint for Koyeb"""
    
    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            response = """
            <html>
            <head>
                <meta charset="UTF-8">
                <title>StreamFlash Bot Status</title>
            </head>
            <body style="font-family: Arial; padding: 20px; background: #f0f0f0;">
                <div style="background: white; padding: 30px; border-radius: 10px; max-width: 600px; margin: 0 auto;">
                    <h1 style="color: #4CAF50;">StreamFlash Telegram Bot</h1>
                    <p style="color: green; font-size: 20px;">Status: RUNNING</p>
                    <p>Health Check: OK</p>
                    <p>Service: Active</p>
                    <hr>
                    <small>Automated Video Posting System</small>
                </div>
            </body>
            </html>
            """
            self.wfile.write(response.encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        # Suppress access logs
        pass

def run_health_server():
    """Run health check server for Koyeb"""
    try:
        port = int(os.getenv('PORT', 8000))
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        print(f"🏥 Health check server running on port {port}")
        server.serve_forever()
    except Exception as e:
        print(f"❌ Health server error: {e}")
        traceback.print_exc()

def main():
    """Main function to start the bot"""
    
    try:
        print("\n" + "="*60)
        print("STREAMFLASH TELEGRAM BOT")
        print("="*60)
        
        # Validate configuration
        print("\n🔧 Validating configuration...")
        if not validate_config():
            print("\n❌ Configuration validation failed!")
            print("Please check your environment variables in Koyeb")
            sys.exit(1)
        
        print("✅ Configuration validated")
        
        # Create Pyrogram client
        print("\n📱 Creating Pyrogram client...")
        app = Client(
            "streamflash_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workdir="."
        )
        print("✅ Pyrogram client created")
        
        # Set app instance for scheduler
        print("\n⏰ Setting up scheduler...")
        set_app_instance(app)
        print("✅ Scheduler configured")
        
        # Setup handlers
        print("\n🔧 Setting up handlers...")
        setup_handlers(app)
        print("✅ Handlers setup complete")
        
        # Setup admin commands
        print("\n👤 Setting up admin commands...")
        setup_admin_commands(app)
        print("✅ Admin commands setup complete")
        
        # Start scheduler
        print("\n⏰ Starting scheduler...")
        run_scheduler()
        print("✅ Scheduler thread started")
        
        # Start health check server
        print("\n🏥 Starting health check server...")
        health_thread = Thread(target=run_health_server, daemon=True)
        health_thread.start()
        print("✅ Health check server started")
        
        print("\n" + "="*60)
        print("✅ BOT STARTED SUCCESSFULLY")
        print("="*60)
        print("\n💡 Bot is now running...")
        print("📥 Monitoring file store channel for new videos")
        print("⏰ Scheduler is posting videos automatically")
        print("🏥 Health check server active on port", os.getenv('PORT', 8000))
        print("\n🛑 Press Ctrl+C to stop\n")
        
        # Run the bot
        print("🚀 Starting Pyrogram client...\n")
        app.run()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR!")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")
        print("\nFull Traceback:")
        traceback.print_exc()
        
        # Keep health server alive for debugging
        print("\n⚠️ Keeping health server alive for debugging...")
        print("Check Koyeb logs for this error message")
        
        import time
        while True:
            time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR IN MAIN!")
        print(f"Error: {e}")
        traceback.print_exc()
        sys.exit(1)
    
