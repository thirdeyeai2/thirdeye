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

# ---------------- MUTE (FIXED) ----------------
async def restrict(user_id):
    data = load()
    try:
        await app.restrict_chat_member(
            data["group_id"],
            user_id,
            permissions={
                "can_send_messages": False,
                "can_send_media_messages": False,
                "can_send_polls": False,
                "can_send_other_messages": False,
                "can_add_web_page_previews": False,
                "can_invite_users": False
            }
        )
        await log(f"🔇 Muted: {user_id}")
    except Exception as e:
        print("Mute error:", e)

# ---------------- UNMUTE (FIXED - MAIN BUG FIX) ----------------
async def unrestrict(user_id):
    data = load()
    try:
        await app.restrict_chat_member(
            data["group_id"],
            user_id,
            permissions={
                "can_send_messages": True,
                "can_send_media_messages": True,
                "can_send_polls": True,
                "can_send_other_messages": True,
                "can_add_web_page_previews": True,
                "can_invite_users": True
            }
        )
        await log(f"🔊 Unmuted: {user_id}")
    except Exception as e:
        print("Unmute error:", e)

# ---------------- CHECKERS ----------------
async def is_admin(user_id, chat_id):
    try:
        m = await app.get_chat_member(chat_id, user_id)
        return m.status in ("administrator", "creator")
    except:
        return False

async def is_member(user_id, chat_id):
    try:
        await app.get_chat_member(chat_id, user_id)
        return True
    except:
        return False

# ---------------- VC LOOP ----------------
async def vc_loop():
    muted = set()
    member_cache = {}

    while True:
        data = load()

        if not data.get("vc_protection"):
            await asyncio.sleep(2)
            continue

        try:
            chat_id = data["group_id"]

            # ---------------- GET VC ----------------
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

            participants = getattr(call, "participants", None)
            if not participants:
                await asyncio.sleep(2)
                continue

            current_users = set()

            for p in participants:

                if not hasattr(p.peer, "user_id"):
                    continue

                user_id = p.peer.user_id
                current_users.add(user_id)

                # ---------------- ADMIN SKIP ----------------
                if await is_admin(user_id, chat_id):
                    continue

                # ---------------- MEMBER CHECK (CACHED) ----------------
                if user_id in member_cache:
                    member = member_cache[user_id]
                else:
                    member = await is_member(user_id, chat_id)
                    member_cache[user_id] = member

                # ---------------- VIDEO CHECK ----------------
                video_on = getattr(p, "video", False) or getattr(p, "presentation", False)

                # ---------------- RULES ----------------
                should_allow = True

                if data.get("mute_non_members") and not member:
                    should_allow = False

                if data.get("mute_video") and video_on:
                    should_allow = False

                if data.get("mute_channel") and hasattr(p.peer, "channel_id"):
                    should_allow = False

                # ---------------- APPLY ----------------
                if should_allow:
                    if user_id in muted:
                        await unrestrict(user_id)   # 🔥 FIXED UNMUTE WORKS NOW
                        muted.remove(user_id)
                else:
                    if user_id not in muted:
                        await restrict(user_id)
                        muted.add(user_id)

            # ---------------- CLEANUP ----------------
            left_users = muted - current_users
            for uid in left_users:
                muted.discard(uid)

            await asyncio.sleep(1)

        except FloodWait as e:
            await asyncio.sleep(e.value)

        except Exception as e:
            print("VC ERROR:", e)
            await asyncio.sleep(3)

# ---------------- MAIN ----------------
async def main():
    await app.start()
    print("🔥 VC ENGINE RUNNING (FIXED MUTE/UNMUTE)")
    await vc_loop()

app.run(main())