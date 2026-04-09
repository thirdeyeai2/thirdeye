import asyncio
import json
import os
from pyrogram import Client
from pyrogram.errors import FloodWait
from pyrogram.raw.functions.phone import GetGroupCall
from pyrogram.raw.types import InputGroupCall

# --- ENVIRONMENT VARIABLES ---
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Load config.json
def load():
    return json.load(open("config.json"))

# Logging function
async def log(text):
    data = load()
    try:
        await app.send_message(data["log_chat_id"], text)
    except:
        pass

# Restrict user (mute)
async def restrict(user_id):
    data = load()
    try:
        await app.restrict_chat_member(
            data["group_id"],
            user_id,
            permissions={}
        )
        await log(f"🔇 Muted: {user_id}")
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except:
        pass

# Unrestrict user (unmute)
async def unrestrict(user_id):
    data = load()
    try:
        await app.promote_chat_member(
            data["group_id"],
            user_id,
            can_send_messages=True
        )
        await log(f"🔊 Unmuted: {user_id}")
    except:
        pass

# Check if user is admin
async def is_admin(user_id):
    data = load()
    try:
        member = await app.get_chat_member(data["group_id"], user_id)
        return member.status in ("administrator", "creator")
    except:
        return False

# Check if user is a member
async def is_member(user_id):
    data = load()
    try:
        await app.get_chat_member(data["group_id"], user_id)
        return True
    except:
        return False

# Main VC protection loop
async def vc_loop():
    muted = set()

    while True:
        data = load()

        if not data.get("vc_protection"):
            await asyncio.sleep(2)
            continue

        try:
            chat = await app.get_chat(data["group_id"])

            if not chat.full_chat or not getattr(chat.full_chat, "call", None):
                await asyncio.sleep(2)
                continue

            call = chat.full_chat.call
            group_call = InputGroupCall(id=call.id, access_hash=call.access_hash)

            result = await app.invoke(GetGroupCall(call=group_call, limit=100))

            for p in result.participants:

                # Skip non-user peers
                if not hasattr(p.peer, "user_id"):
                    continue

                user_id = p.peer.user_id

                # Skip admins
                if await is_admin(user_id):
                    continue

                # Channel detection
                if hasattr(p.peer, "channel_id") and data.get("mute_channel"):
                    await restrict(user_id)
                    continue

                member = await is_member(user_id)

                # Non-member
                if data.get("mute_non_members") and not member:
                    if user_id not in muted:
                        await restrict(user_id)
                        muted.add(user_id)

                # Member join → unmute
                if member and user_id in muted:
                    await unrestrict(user_id)
                    muted.remove(user_id)

                # Video detection
                if data.get("mute_video") and getattr(p, "video", False):
                    await restrict(user_id)

            await asyncio.sleep(1)

        except Exception as e:
            print("Error:", e)
            await asyncio.sleep(3)

# Main start
async def main():
    await app.start()
    print("🔥 USERBOT RUNNING")
    await vc_loop()

app.run(main())