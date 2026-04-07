import asyncio
import os
from datetime import datetime
from pyrogram import Client
from pyrogram.raw import functions, types
import time

# ==================== CONFIG ====================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = int(os.getenv("GROUP_ID"))
VC_CHECK_INTERVAL = 0.5  # ultra-fast monitoring
# ================================================

# Force UTC timezone
os.environ['TZ'] = 'UTC'
time.tzset()

# ==================== APP ========================
app = Client(
    "vcghost",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

muted_users = set()

# ----------------- TIME SYNC -------------------
async def force_time_sync():
    """Force Pyrogram to sync session time with Telegram."""
    while True:
        try:
            ts = int(datetime.utcnow().timestamp() * 1000)
            await app.send(functions.Ping(ping_id=ts))
            return
        except Exception:
            await asyncio.sleep(0.5)  # retry fast

# ----------------- MUTE FUNCTION ----------------
async def mute_participant(call, user_id, mute=True):
    try:
        await app.send(
            functions.phone.ToggleGroupCallParticipant(
                call=call,
                participant=user_id,
                muted=mute
            )
        )
        print(f"{'Muted' if mute else 'Unmuted'} {user_id}")
    except Exception as e:
        print(f"Error muting {user_id}: {e}")

# ----------------- SUPER GHOST VC -----------------
async def ghost_vc_controller():
    await app.start()
    print("⏳ Syncing time with Telegram...")
    await force_time_sync()
    print("⏱️ Time synced! Ghost VC running...")

    while True:
        try:
            # Keep time synced to avoid [16]
            await force_time_sync()

            # Fetch VC participants
            group_call = await app.send(
                functions.phone.GetGroupCallRequest(
                    peer=types.InputPeerChannel(channel_id=GROUP_ID, access_hash=0),
                    limit=100
                )
            )
            participants = group_call.participants

            for p in participants:
                user_id = p.user_id
                user = await app.get_users(user_id)
                member_status = await app.get_chat_member(GROUP_ID, user_id)

                # Skip admins
                if member_status.status in ["administrator", "creator"]:
                    continue

                # Auto-mute bots, non-members, or video users
                if user.is_bot or not member_status.is_member or getattr(p, "video", False):
                    if user_id not in muted_users:
                        await mute_participant(group_call, user_id, True)
                        muted_users.add(user_id)
                    continue

                # Auto-unmute if previously muted and now member
                if user_id in muted_users and member_status.is_member:
                    await mute_participant(group_call, user_id, False)
                    muted_users.remove(user_id)

        except Exception as e:
            print(f"⚠️ VC loop error: {e}")

        await asyncio.sleep(VC_CHECK_INTERVAL)

# ----------------- RUN -------------------------
if __name__ == "__main__":
    asyncio.run(ghost_vc_controller())