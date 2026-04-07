import asyncio
from pyrogram import Client
from pyrogram.raw import functions, types
from datetime import datetime
import os

# ==================== CONFIG ====================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = int(os.getenv("GROUP_ID"))
VC_CHECK_INTERVAL = 1  # seconds for ultra-fast monitoring
# ================================================

app = Client(
    "vcghost",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

muted_users = set()  # track muted users for auto-unmute

# ----------------- TIME SYNC -------------------
async def sync_time():
    """Fix [16] msg_id too low error by syncing time with Telegram."""
    await app.send(functions.Ping(ping_id=int(datetime.now().timestamp() * 1000)))

# ----------------- MUTE FUNCTION ----------------
async def mute_participant(call, user_id, mute=True):
    """Mute/unmute a user in VC"""
    try:
        await app.send(
            functions.phone.ToggleGroupCallParticipant(
                call=call,
                participant=user_id,
                muted=mute
            )
        )
        print(f"{'Muted' if mute else 'Unmuted'} user {user_id}")
    except Exception as e:
        print(f"Error muting {user_id}: {e}")

# ----------------- GHOST VC MONITOR ------------------
async def monitor_vc():
    await app.start()
    await sync_time()
    print("🚀 Ghost VC Controller Running in Ultra Invisible Mode...")

    while True:
        try:
            # Get group call info
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

                # Admin exemption
                if member_status.status in ["administrator", "creator"]:
                    continue

                # Auto-mute bots, channels, non-members, or video
                if user.is_bot or not member_status.is_member or getattr(p, "video", False):
                    await mute_participant(group_call, user_id, True)
                    muted_users.add(user_id)
                    continue

                # Auto unmute if previously muted and now a member
                if user_id in muted_users and member_status.is_member:
                    await mute_participant(group_call, user_id, False)
                    muted_users.remove(user_id)

        except Exception as e:
            print(f"Error in VC loop: {e}")

        await asyncio.sleep(VC_CHECK_INTERVAL)

# ----------------- RUN -------------------------
if __name__ == "__main__":
    asyncio.run(monitor_vc())