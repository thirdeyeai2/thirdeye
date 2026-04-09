import os
import json
from pyrogram import Client, filters

# --- ENVIRONMENT VARIABLES ---
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Client("control_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Load and save config.json
def load():
    return json.load(open("config.json"))

def save(data):
    json.dump(data, open("config.json", "w"), indent=4)

# --- COMMAND HANDLERS ---
@bot.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply_text(
        "🤖 VC CONTROL PANEL\n\n"
        "/on - Enable VC Protection\n"
        "/off - Disable VC Protection\n"
        "/nonmember - Toggle Non-member mute\n"
        "/channel - Toggle Channel mute\n"
        "/video - Toggle Video mute\n"
        "/status - Show settings"
    )

@bot.on_message(filters.command("on"))
async def on(_, msg):
    data = load()
    data["vc_protection"] = True
    save(data)
    await msg.reply("✅ VC Protection Enabled")

@bot.on_message(filters.command("off"))
async def off(_, msg):
    data = load()
    data["vc_protection"] = False
    save(data)
    await msg.reply("❌ VC Protection Disabled")

@bot.on_message(filters.command("nonmember"))
async def nonmember(_, msg):
    data = load()
    data["mute_non_members"] = not data.get("mute_non_members", False)
    save(data)
    await msg.reply(f"Non-member mute: {data['mute_non_members']}")

@bot.on_message(filters.command("channel"))
async def channel(_, msg):
    data = load()
    data["mute_channel"] = not data.get("mute_channel", False)
    save(data)
    await msg.reply(f"Channel mute: {data['mute_channel']}")

@bot.on_message(filters.command("video"))
async def video(_, msg):
    data = load()
    data["mute_video"] = not data.get("mute_video", False)
    save(data)
    await msg.reply(f"Video mute: {data['mute_video']}")

@bot.on_message(filters.command("status"))
async def status(_, msg):
    data = load()
    await msg.reply(f"⚙️ SETTINGS:\n\n{data}")

# --- START BOT ---
bot.run()