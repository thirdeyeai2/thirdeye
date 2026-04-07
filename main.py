import asyncio
from pyrogram import Client, enums
from pyrogram.raw import functions, types
from datetime import datetime

# ==================== CONFIG ====================
API_ID = int("YOUR_API_ID")
API_HASH = "YOUR_API_HASH")
SESSION_STRING = "YOUR_SESSION_STRING"
GROUP_ID = -1001234567890  # Your group ID
VC_CHECK_INTERVAL = 2  # Check every 2 seconds
# ================================================

app = Client(
    "vcghost",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

async def sync_time():
    """Fix [16] msg_id too low by syncing time with Telegram."""
    await app.send(functions.Ping(ping_id=int(datetime.now().timestamp() * 1000)))

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
                    continue

                # Channel / bot / non-member auto-mute
                if user.is_bot or not member_status.is_member:
                    await mute_participant(group_call, user_id, True)
                    continue

                # Video detection mute
                if getattr(p, "video", False):
                    await mute_participant(group_call, user_id, True)

            await asyncio.sleep(VC_CHECK_INTERVAL)

        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(VC_CHECK_INTERVAL)

# ========== Run ==========
asyncio.run(monitor_vc())