from pyrogram import Client
import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_NAME = "ultra_v5_session"

app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)

print("💡 Starting login... Enter phone and code in Railway console.")

with app:
    session_string = app.export_session_string()
    print("✅ Session created successfully!")
    print("💾 Copy this SESSION_STRING and add to Railway Variables:")
    print(session_string)