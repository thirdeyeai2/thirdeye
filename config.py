
import json
import os

with open("data.json") as f:
    d = json.load(f)

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

GROUPS = d["groups"]