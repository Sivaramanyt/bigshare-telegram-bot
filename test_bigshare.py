"""Test BigShare API authentication"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("BIGSHARE_API_URL", "https://bigshare.io/api/upload")
TOKEN = os.getenv("BIGSHARE_TOKEN", "")

print(f"Testing BigShare API...")
print(f"URL: {API_URL}")
print(f"Token: {TOKEN[:20]}... (length: {len(TOKEN)})")
print()

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "User-Agent": "Test/1.0"
}

# Test with a simple URL upload
test_url = "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4"

print(f"Testing URL upload: {test_url}")
print()

try:
    response = requests.post(
        API_URL,
        headers=headers,
        data={'url': test_url},
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Response Length: {len(response.text)}")
    print()
    
    if 'text/html' in response.headers.get('Content-Type', ''):
        print("❌ PROBLEM: Got HTML response (login page)")
        print("   This means authentication failed!")
        print()
        print("Possible issues:")
        print("1. Token is wrong or expired")
        print("2. Token format is incorrect")
        print("3. API endpoint is wrong")
        print()
        print("Response preview:")
        print(response.text[:500])
    else:
        print("✅ Got non-HTML response (likely JSON)")
        print()
        try:
            json_data = response.json()
            print(f"JSON Response: {json_data}")
        except:
            print(f"Response: {response.text}")
            
except Exception as e:
    print(f"❌ Error: {e}")
