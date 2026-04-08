import asyncio
import os
import time
from datetime import datetime
from pyrogram import Client
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.phone import (
    GetGroupCall,
    EditGroupCallParticipant,
    JoinGroupCall,
    LeaveGroupCall
)
from pyrogram.raw.types import InputGroupCall

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = os.getenv("GROUP_ID")  # USE @username

CHECK_INTERVAL = 1   # safe speed
GHOST_DELAY = 0.5    # ghost join time

# ================= APP ====================
app = Client(
    "ultra_v4_elite",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    no_updates=True   # 🔥 CRITICAL FIX
)

# ================= STATE ==================
muted_users = set()
last_participants = {}

cached_call = None
last_call_fetch = 0

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
        if time.time() - last_call_fetch < 15 and cached_call:
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

# ----------------- GHOST JOIN ----------------
async def ghost_cycle(call):
    try:
        # 🔥 get your own peer (important)
        me = await app.get_me()
        join_as = await app.resolve_peer(me.id)

        await app.invoke(JoinGroupCall(
            call=call,
            join_as=join_as,   # ✅ FIX HERE
            muted=True,
            video_stopped=True,
            params=b""
        ))

        await asyncio.sleep(GHOST_DELAY)

        await app.invoke(LeaveGroupCall(call=call))

        log("👻 Ghost cycle executed")

    except Exception as e:
        log(f"⚠️ Ghost error: {e}")

# ----------------- MAIN LOOP ----------------
async def ultra_v4_elite():
    log("🚀 ULTRA V4 ELITE STARTED")

    await app.start()

    # Ensure joined group (run once safety)
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

            # 👻 Ghost monitoring
            await ghost_cycle(group_call)

            current_users = {}

            for p in group_call.participants:
                participant = getattr(p, "participant", None)
                if not participant or not hasattr(participant, "user_id"):
                    continue

                user_id = participant.user_id
                video = getattr(participant, "video_enabled", False)

                current_users[user_id] = video

                # 🔥 process only changes
                if user_id not in last_participants or last_participants[user_id] != video:

                    try:
                        member = await app.get_chat_member(GROUP_ID, user_id)
                    except:
                        continue

                    # 👑 skip admins
                    if member.status in ["administrator", "creator"]:
                        continue

                    # 🚫 not member / channel account
                    if not member.is_member:
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

                    # 🔊 auto unmute
                    if user_id in muted_users:
                        await mute_user(group_call, user_id, False)
                        muted_users.remove(user_id)

            # 🧹 cleanup left users
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
    asyncio.run(ultra_v4_elite())