"""
BigShare Telegram Bot - Main Entry Point
Automated video posting system with BigShare integration
"""

from pyrogram import Client
from pyrogram.errors import FloodWait
from config import API_ID, API_HASH, BOT_TOKEN, validate_config
from handlers import setup_handlers
from admin import setup_admin_commands
from scheduler import run_scheduler, set_app_instance
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import time

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
                <title>BigShare Bot Status</title>
            </head>
            <body style="font-family: Arial; padding: 20px; background: #f0f0f0;">
                <div style="background: white; padding: 30px; border-radius: 10px; max-width: 600px; margin: 0 auto;">
                    <h1 style="color: #4CAF50;">BigShare Telegram Bot</h1>
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
        pass

def run_health_server():
    """Run health check server for Koyeb"""
    port = int(os.getenv('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"Health check server running on port {port}")
    server.serve_forever()

def main():
    """Main function to start the bot"""
    
    print("\n" + "="*50)
    print("BIGSHARE TELEGRAM BOT")
    print("="*50)
    
    # Validate configuration
    if not validate_config():
        print("\nPlease configure .env file properly")
        print("Copy .env.example to .env and fill in your details")
        return
    
    print("Configuration validated")
    
    # Create Pyrogram client with session persistence
    app = Client(
        "bigshare_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        workdir="."  # Save session in current directory
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
    print("BOT STARTED SUCCESSFULLY")
    print("="*50)
    print("\nBot is now running...")
    print("Monitoring file store channel for new videos")
    print("Scheduler is posting videos automatically")
    print("Health check server active on port", os.getenv('PORT', 8000))
    print("\nPress Ctrl+C to stop\n")
    
    # Run the bot with flood wait handling
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            app.run()
            break  # Success, exit loop
            
        except FloodWait as e:
            wait_time = e.value
            retry_count += 1
            print(f"\nFlood Wait: Telegram requires {wait_time} seconds wait")
            print(f"Attempt {retry_count}/{max_retries}")
            print(f"Waiting {wait_time + 5} seconds before retry...")
            
            if retry_count >= max_retries:
                print("\nMax retries reached. Please wait a few minutes and redeploy.")
                print("Keeping health server alive...")
                # Keep health server running
                while True:
                    time.sleep(60)
            else:
                time.sleep(wait_time + 5)
                
        except KeyboardInterrupt:
            print("\n\nBot stopped by user")
            break
            
        except Exception as e:
            print(f"\n\nFatal error: {e}")
            import traceback
            traceback.print_exc()
            
            # Keep health server alive to prevent restart loop
            print("\nKeeping health server alive...")
            while True:
                time.sleep(60)

if __name__ == "__main__":
    main()
    
