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
    approved = set()
    member_cache = {}

    while True:
        data = load()

        if not data.get("vc_protection"):
            await asyncio.sleep(2)
            continue

        try:
            chat_id = data["group_id"]

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

                # ---------------- CACHE MEMBER CHECK ----------------
                if user_id in member_cache:
                    is_member = member_cache[user_id]
                else:
                    try:
                        m = await app.get_chat_member(chat_id, user_id)
                        is_member = True
                        member_cache[user_id] = True
                    except:
                        is_member = False
                        member_cache[user_id] = False

                # ---------------- ADMIN SKIP ----------------
                try:
                    m = await app.get_chat_member(chat_id, user_id)
                    if m.status in ("administrator", "creator"):
                        continue
                except:
                    pass

                # ---------------- VIDEO CHECK ----------------
                video_on = getattr(p, "video", False) or getattr(p, "presentation", False)

                # ---------------- RULE ENGINE ----------------
                should_allow = True

                # Rule 1: Non-member
                if data.get("mute_non_members") and not is_member:
                    should_allow = False

                # Rule 2: Video restriction
                if data.get("mute_video") and video_on:
                    should_allow = False

                # Rule 3: Channel restriction (if available)
                if data.get("mute_channel") and hasattr(p.peer, "channel_id"):
                    should_allow = False

                # ---------------- APPLY ACTION ----------------
                if should_allow:
                    if user_id not in approved:
                        await unrestrict(user_id)
                        approved.add(user_id)
                        muted.discard(user_id)
                else:
                    if user_id not in muted:
                        await restrict(user_id)
                        muted.add(user_id)
                        approved.discard(user_id)

            # ---------------- CLEANUP (LEFT VC USERS) ----------------
            left_users = (muted | approved) - current_users

            for uid in left_users:
                muted.discard(uid)
                approved.discard(uid)

            await asyncio.sleep(1)

        except Exception as e:
            print("VC ERROR:", e)
            await asyncio.sleep(3)

# ---------------- MAIN ----------------
async def main():
    await app.start()
    print("🔥 ELITE VC ENGINE RUNNING (STABLE MODE)")
    await vc_loop()

app.run(main())