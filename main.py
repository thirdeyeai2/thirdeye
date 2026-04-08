import asyncio
import os
import time
from datetime import datetime
from pyrogram import Client
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.phone import (
    GetGroupCall,
    EditGroupCallParticipant,
    JoinGroupCall
)
from pyrogram.raw.types import InputGroupCall, DataJSON

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = os.getenv("GROUP_ID")  # ONLY @username or chat ID

CHECK_INTERVAL = 1  # seconds

# ================= APP ====================
app = Client(
    "ultra_v5_stable",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    no_updates=True
)

# ================= STATE ==================
muted_users = set()
last_participants = {}

member_cache = {}
member_cache_time = {}

vc_joined = False
JOIN_AS = None

# ----------------- LOGGER ----------------
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ----------------- GET VC ----------------
async def get_group_call():
    """Fetch the current VC if it exists."""
    try:
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
        return group_call
    except Exception as e:
        return None

# ----------------- JOIN VC SAFELY ----------------
async def ensure_vc_join(group_call):
    """Join the VC only if it exists."""
    global vc_joined, JOIN_AS

    if vc_joined or not group_call:
        return False

    try:
        await app.invoke(JoinGroupCall(
            call=group_call.call,
            join_as=JOIN_AS,
            muted=True,
            video_stopped=True,
            params=DataJSON(data='{"U":"1"}')
        ))
        vc_joined = True
        log("👻 VC joined successfully")
        return True
    except Exception as e:
        # Do not print GROUPCALL_INVALID
        return False

# ----------------- MEMBER CHECK ----------------
async def is_valid_member(user_id):
    now = time.time()
    if user_id in member_cache and now - member_cache_time[user_id] < 30:
        return member_cache[user_id]
    try:
        member = await app.get_chat_member(GROUP_ID, user_id)
        result = member.status in ["administrator", "creator"] or member.is_member
    except:
        result = False
    member_cache[user_id] = result
    member_cache_time[user_id] = now
    return result

# ----------------- MUTE ----------------
async def mute_user(call, user_id, mute=True):
    try:
        await app.invoke(EditGroupCallParticipant(
            call=call.call,
            participant=user_id,
            muted=mute
        ))
        log(f"{'🔇 Muted' if mute else '🔊 Unmuted'}: {user_id}")
    except Exception as e:
        log(f"⚠️ Mute error {user_id}: {e}")

# ----------------- MAIN LOOP ----------------
async def ultra_v5_stable():
    global JOIN_AS, vc_joined

    log("🚀 ULTRA V5 STABLE STARTED")
    await app.start()

    # Cache self peer (avoid flood)
    me = await app.get_me()
    JOIN_AS = await app.resolve_peer(me.id)

    while True:
        try:
            group_call = await get_group_call()

            # Wait for VC to exist before doing anything
            if not group_call:
                vc_joined = False
                await asyncio.sleep(3)
                continue

            # Join VC safely if not already
            await ensure_vc_join(group_call)

            current_users = {}
            for p in group_call.participants:
                participant = getattr(p, "participant", None)
                if not participant or not hasattr(participant, "user_id"):
                    continue
                user_id = participant.user_id
                video = getattr(participant, "video_enabled", False)
                current_users[user_id] = video

                # Only act if status changed
                if user_id not in last_participants or last_participants[user_id] != video:
                    valid = await is_valid_member(user_id)

                    # Non-member / channel → mute
                    if not valid:
                        if user_id not in muted_users:
                            await mute_user(group_call, user_id, True)
                            muted_users.add(user_id)
                        continue

                    # Video ON → mute
                    if video:
                        if user_id not in muted_users:
                            await mute_user(group_call, user_id, True)
                            muted_users.add(user_id)
                        continue

                    # Auto unmute
                    if user_id in muted_users:
                        await mute_user(group_call, user_id, False)
                        muted_users.remove(user_id)

            # Cleanup users who left VC
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
    asyncio.run(ultra_v5_stable())