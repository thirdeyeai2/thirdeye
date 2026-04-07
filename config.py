import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# userbot session (string session recommended)
SESSION = os.getenv("SESSION")

# groups to protect
PROTECTED_GROUPS = {
    -1003844395600: True,  # replace with your group ID
}