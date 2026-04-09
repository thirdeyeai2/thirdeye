import asyncio
import json
import os
from pyrogram import Client
from pyrogram.errors import FloodWait
from pyrogram.raw.functions.phone import GetGroupCall
from pyrogram.raw.types import InputGroupCall

# ---------------- ENV ----------------
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")

app = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# ---------------- CONFIG ----------------
def load():
    return json.load(open("config.json"))

async def log(text):
    try:
        data = load()
        await app.send_message(data["log_chat_id"], text)
    except:
        pass

# ---------------- ACTIONS ----------------
async def restrict(user_id):
    try:
        data = load()
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

async def unrestrict(user_id):
    try:
        data = load()
        await app.unban_chat_member(data["group_id"], user_id)
        await log(f"🔊 Unmuted: {user_id}")
    except:
        pass

# ---------------- CHECKERS ----------------
async def is_admin(user_id):
    try:
        data = load()
        m = await app.get_chat_member(data["group_id"], user_id)
        return m.status in ("administrator", "creator")
    except:
        return False

async def is_member(user_id):
    try:
        data = load()
        await app.get_chat_member(data["group_id"], user_id)
        return True
    except:
        return False

# ---------------- ELITE VC LOOP ----------------
async def vc_loop():
    muted = set()

    while True:
        data = load()

        if not data.get("vc_protection"):
            await asyncio.sleep(2)
            continue

        try:
            chat_id = data["group_id"]

            # 🔥 SAFE VC CHECK (NO full_chat)
            try:
                call = await app.invoke(
                    GetGroupCall(
                        call=InputGroupCall(
                            id=chat_id,
                            access_hash=0
                        ),
                        limit=100
                    )
                )
            except:
                await asyncio.sleep(3)
                continue

            # No participants safety check
            if not hasattr(call, "participants"):
                await asyncio.sleep(2)
                continue

            for p in call.participants:

                # skip invalid peers
                if not hasattr(p.peer, "user_id"):
                    continue

                user_id = p.peer.user_id

                # skip admins
                if await is_admin(user_id):
                    continue

                member = await is_member(user_id)

                # mute non-members
                if data.get("mute_non_members") and not member:
                    if user_id not in muted:
                        await restrict(user_id)
                        muted.add(user_id)

                # unmute if returned
                if member and user_id in muted:
                    await unrestrict(user_id)
                    muted.remove(user_id)

                # video mute
                if data.get("mute_video") and getattr(p, "video", False):
                    await restrict(user_id)

            await asyncio.sleep(1)

        except FloodWait as e:
            await asyncio.sleep(e.value)

        except Exception as e:
            print("VC ERROR:", e)
            await asyncio.sleep(3)

# ---------------- MAIN ----------------
async def main():
    await app.start()
    print("🔥 ELITE VC ENGINE RUNNING (STABLE MODE)")
    await vc_loop()

app.run(main())