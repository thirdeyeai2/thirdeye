import asyncio
from pyrogram import Client, enums
from pyrogram.raw import functions, types
from datetime import datetime
import os

# ==================== CONFIG ====================
API_ID = int(os.getenv("API_ID"))           # Railway Variable: API_ID
API_HASH = os.getenv("API_HASH")            # Railway Variable: API_HASH
SESSION_STRING = os.getenv("SESSION_STRING")  # Railway Variable: SESSION_STRING
GROUP_ID = int(os.getenv("GROUP_ID"))       # Railway Variable: GROUP_ID
VC_CHECK_INTERVAL = int(os.getenv("VC_CHECK_INTERVAL", 2))  # default 2 seconds
# ================================================

app = Client(
    "vcghost",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# Dictionary to keep track of muted users for auto-unmute
muted_users = {}

async def sync_time():
    """Fix [16] msg_id too low by syncing time with Telegram."""
    await app.send(
        functions.Ping(
            ping_id=int(datetime.now().timestamp() * 1000)
        )
    )

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
        if mute:
            muted_users[user_id] = True
            print(f"🔇 Muted user {user_id}")
        else:
            muted_users.pop(user_id, None)
            print(f"🔊 Unmuted user {user_id}")
    except Exception as e:
        print(f"Error muting/unmuting {user_id}: {e}")

async def monitor_vc():
    await app.start()
    await sync_time()
    print("🚀 VC Ghost Controller Running...")

    while True:
        try:
            # Get group call
            group_call = await app.send(
                functions.phone.GetGroupCallRequest(
                    peer=types.InputPeerChannel(channel_id=GROUP_ID, access_hash=0),
                    limit=100
                )
            )

            participants = group_call.participants

            for p in participants:
                user_id = p.user_id

                # Fetch user info
                user = await app.get_users(user_id)

                # Admin exemption
                member_status = await app.get_chat_member(GROUP_ID, user_id)
                if member_status.status in ["administrator", "creator"]:
                    # Auto-unmute admins if previously muted
                    if muted_users.get(user_id):
                        await mute_participant(group_call, user_id, mute=False)
                    continue

                # Non-member auto-mute
                if not member_status.is_member:
                    await mute_participant(group_call, user_id, True)
                    continue

                # Channel account / bot auto-mute
                if user.is_bot:
                    await mute_participant(group_call, user_id, True)
                    continue

                # Video detection mute
                if getattr(p, "video", False):
                    await mute_participant(group_call, user_id, True)
                    continue

                # Auto unmute if previously muted but now member
                if muted_users.get(user_id) and member_status.is_member:
                    await mute_participant(group_call, user_id, mute=False)

            # Always monitoring
            await asyncio.sleep(VC_CHECK_INTERVAL)

        except Exception as e:
            print(f"⚠️ Error: {e}")
            await asyncio.sleep(VC_CHECK_INTERVAL)

# ========== Run ==========
asyncio.run(monitor_vc())