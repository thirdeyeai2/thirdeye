import asyncio
import os
from datetime import datetime
from pyrogram import Client
from pyrogram.errors import PeerIdInvalid
from pyrogram.raw.functions.phone import GetGroupCall, EditGroupCallParticipant
from pyrogram.raw.types import InputPeerChannel

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = int(os.getenv("GROUP_ID"))

VC_CHECK_INTERVAL = 1       # Check VC every 1 sec
GHOST_LEAVE_DELAY = 0.5     # Leave VC in 0.5 sec for stealth

# ================= APP ====================
app = Client("vcghost_auto", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
muted_users = set()

# ----------------- MUTE FUNCTION ----------------
async def mute_user(call, user_id, mute=True):
    try:
        await app.invoke(EditGroupCallParticipant(
            call=call,
            participant=user_id,
            muted=mute
        ))
        print(f"{'Muted' if mute else 'Unmuted'} {user_id} at {datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        print(f"⚠️ Error muting/unmuting {user_id}: {e}")

# ----------------- ULTRA GHOST VC MONITOR ------------------
async def ultra_ghost_monitor():
    await app.start()
    print("⏱️ Time synced! Ultra Ghost VC running...")

    try:
        chat = await app.get_chat(GROUP_ID)
        peer = InputPeerChannel(channel_id=chat.id, access_hash=chat.access_hash)
    except PeerIdInvalid:
        print(f"❌ Invalid GROUP_ID: {GROUP_ID}")
        return

    while True:
        try:
            group_call = await app.invoke(GetGroupCall(peer=peer))
            participants = getattr(group_call, "participants", [])

            for p in participants:
                user_id = p.user_id
                member_status = await app.get_chat_member(GROUP_ID, user_id)

                # ✅ Admin exemption
                if member_status.status in ["administrator", "creator"]:
                    continue

                # ✅ Non-member auto-mute
                if not member_status.is_member:
                    if user_id not in muted_users:
                        await mute_user(group_call, user_id, True)
                        muted_users.add(user_id)
                    continue

                # ✅ Video detection mute
                if getattr(p, "video_enabled", False):
                    if user_id not in muted_users:
                        await mute_user(group_call, user_id, True)
                        muted_users.add(user_id)
                    continue

                # ✅ Channel account detection (channels not allowed in VC)
                if getattr(p, "user_id", 0) < 0 and str(user_id).startswith("-100"):  # simple check
                    if user_id not in muted_users:
                        await mute_user(group_call, user_id, True)
                        muted_users.add(user_id)
                    continue

                # ✅ Auto-unmute on joining group
                if user_id in muted_users and member_status.is_member:
                    await mute_user(group_call, user_id, False)
                    muted_users.remove(user_id)

            # ✅ Ghost leave (ultra stealth)
            await asyncio.sleep(GHOST_LEAVE_DELAY)

        except PeerIdInvalid:
            print("❌ Peer ID invalid, retrying...")
        except Exception as e:
            print(f"⚠️ VC loop error: {e}")

        await asyncio.sleep(VC_CHECK_INTERVAL)

# ----------------- AUTO-DETECT VC START -----------------
async def detect_and_run():
    while True:
        try:
            await ultra_ghost_monitor()
        except Exception as e:
            print(f"🔥 Crash detected: {e}")
            print("♻️ Restarting in 5 seconds...")
            await asyncio.sleep(5)

# ----------------- RUN -------------------------
if __name__ == "__main__":
    asyncio.run(detect_and_run())