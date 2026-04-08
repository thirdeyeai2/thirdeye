import asyncio
import os
import time
from datetime import datetime
from pyrogram import Client
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.phone import GetGroupCall, EditGroupCallParticipant
from pyrogram.raw.types import InputGroupCall

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = os.getenv("GROUP_ID")  # @username

CHECK_INTERVAL = 1

# ================= APP ====================
app = Client(
    "ultra_v5_stealth",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    no_updates=True  # 🔥 no peer errors
)

# ================= STATE ==================
muted_users = set()
last_participants = {}

cached_call = None
last_call_fetch = 0

member_cache = {}
member_cache_time = {}

# ----------------- LOGGER ----------------
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ----------------- MUTE ----------------
async def mute_user(call, user_id, mute=True):
    try:
        await app.invoke(EditGroupCallParticipant(
            call=call,
            participant=user_id,
            muted=mute
        ))
        log(f"{'🔇 Muted' if mute else '🔊 Unmuted'}: {user_id}")
    except Exception as e:
        log(f"⚠️ Mute error {user_id}: {e}")

# ----------------- GET VC ----------------
async def get_group_call():
    global cached_call, last_call_fetch

    try:
        if time.time() - last_call_fetch < 10 and cached_call:
            return cached_call

        peer = await app.resolve_peer(GROUP_ID)
        full_chat = await app.invoke(GetFullChannel(channel=peer))

        call = getattr(full_chat.full_chat, "call", None)
        if not call:
            return None

        group_call = await app.invoke(
            GetGroupCall(
                call=InputGroupCall(
                    id=call.id,
                    access_hash=call.access_hash
                ),
                limit=100
            )
        )

        cached_call = group_call
        last_call_fetch = time.time()

        return group_call

    except Exception as e:
        log(f"⚠️ Get VC error: {e}")
        return None

# ----------------- MEMBER CHECK (SMART CACHE) ----------------
async def is_valid_member(user_id):
    now = time.time()

    # 🔥 cache for 30 sec
    if user_id in member_cache and now - member_cache_time[user_id] < 30:
        return member_cache[user_id]

    try:
        member = await app.get_chat_member(GROUP_ID, user_id)

        if member.status in ["administrator", "creator"]:
            result = True
        else:
            result = member.is_member

    except:
        result = False

    member_cache[user_id] = result
    member_cache_time[user_id] = now

    return result

# ----------------- MAIN LOOP ----------------
async def ultra_v5():
    log("🚀 ULTRA V5 STEALTH STARTED")

    await app.start()

    # safety join once
    try:
        await app.join_chat(GROUP_ID)
    except:
        pass

    while True:
        try:
            group_call = await get_group_call()

            if not group_call or not hasattr(group_call, "participants"):
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            current_users = {}

            for p in group_call.participants:
                participant = getattr(p, "participant", None)
                if not participant or not hasattr(participant, "user_id"):
                    continue

                user_id = participant.user_id
                video = getattr(participant, "video_enabled", False)

                current_users[user_id] = video

                # ⚡ only changes
                if user_id not in last_participants or last_participants[user_id] != video:

                    valid = await is_valid_member(user_id)

                    # 🚫 not member / channel
                    if not valid:
                        if user_id not in muted_users:
                            await mute_user(group_call, user_id, True)
                            muted_users.add(user_id)
                        continue

                    # 🎥 video ON
                    if video:
                        if user_id not in muted_users:
                            await mute_user(group_call, user_id, True)
                            muted_users.add(user_id)
                        continue

                    # 🔊 unmute
                    if user_id in muted_users:
                        await mute_user(group_call, user_id, False)
                        muted_users.remove(user_id)

            # cleanup left users
            for old_user in list(last_participants.keys()):
                if old_user not in current_users:
                    muted_users.discard(old_user)

            last_participants.clear()
            last_participants.update(current_users)

        except Exception as e:
            log(f"⚠️ Loop error: {e}")

        await asyncio.sleep(CHECK_INTERVAL)

# ----------------- RUN ----------------
if __name__ == "__main__":
    asyncio.run(ultra_v5())