import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_STRING = os.getenv("SESSION_STRING")

GROUP_ID = int(os.getenv("GROUP_ID"))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL"))

PORT = int(os.getenv("PORT", 8000))