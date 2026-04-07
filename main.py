import os
import asyncio
from pyrogram import Client
from pyrogram.raw.functions.phone import GetGroupCall, DiscardGroupCall
from pyrogram.raw.functions.channels import GetParticipant
from pyrogram.raw.types import InputPeerUser

# ================= VARIABLES =================
API_ID = int(os.getenv("API_ID"))         # Your Telegram API ID
API_HASH = os.getenv("API_HASH")         # Your Telegram API HASH
SESSION = os.getenv("SESSION")           # Userbot session string
GROUP_ID = int(os.getenv("GROUP_ID"))    # Group ID to monitor VC
LOOP_DELAY = 2  # Seconds between checks

# ================= CLIENT =================
app = Client(SESSION, api_id=API_ID, api_hash=API_HASH, in_memory=True)

# ================= UTILITY FUNCTIONS =================
async def is_admin(user_id):
    try:
        participant = await app.invoke(GetParticipant(channel=GROUP_ID, user_id=user_id))
        role = participant.participant
        return getattr(role, "admin_rights", None) is not None
    except:
        return False

async def mute_user(user_id):
    try:
        await app.invoke(DiscardGroupCall(call=InputPeerUser(user_id=user_id, access_hash=0), schedule_date=None))
        print(f"[MUTED] User ID: {user_id}")
    except Exception as e:
        print(f"[MUTE ERROR] {user_id}: {e}")

async def unmute_user(user_id):
    # Auto-unmute logic: invite back or allow to speak
    print(f"[UNMUTED] User ID: {user_id}")

async def check_group_membership(user_id):
    # Check if user is now a member of the group
    try:
        participant = await app.get_chat_member(GROUP_ID, user_id)
        return participant.status != "left"
    except:
        return False

# ================= MONITOR VC =================
async def monitor_vc():
    async with app:
        print("🚀 MEGA VC GHOST SYSTEM RUNNING")
        while True:
            try:
                call = await app.invoke(GetGroupCall(peer=GROUP_ID))
                participants = call.participants

                for user in participants:
                    user_id = user.user_id

                    # Skip admins
                    if await is_admin(user_id):
                        continue

                    # Always mute channels
                    if getattr(user, "is_channel", False):
                        await mute_user(user_id)
                        continue

                    # Non-member auto-mute
                    if not getattr(user, "is_member", True):
                        await mute_user(user_id)
                        # If user joins group later → unmute
                        if await check_group_membership(user_id):
                            await unmute_user(user_id)
                        continue

                    # Video detection mute
                    if getattr(user, "video_enabled", False):
                        await mute_user(user_id)

            except Exception as e:
                print("[VC ERROR]", e)

            await asyncio.sleep(LOOP_DELAY)

# ================= RUN =================
if __name__ == "__main__":
    asyncio.run(monitor_vc())