import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.phone import GetGroupCallRequest, ToggleGroupCallParticipant
from telethon.tl.functions.channels import GetParticipantRequest

# ====== ENV VARIABLES ======
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")  # StringSession
TARGET_GROUP = int(os.getenv("TARGET_GROUP"))  # Group/channel ID to monitor

# ====== CLIENT SETUP (Invisible) ======
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ====== HELPER FUNCTIONS ======
async def get_vc_participants():
    """Get all participants in the VC."""
    try:
        call = await client(GetGroupCallRequest(TARGET_GROUP))
        participants = await client.get_participants(call.call)
        return participants
    except Exception as e:
        print(f"[VC Error] {e}")
        return []

async def is_admin(user_id):
    """Check if user is admin."""
    try:
        participant = await client(GetParticipantRequest(TARGET_GROUP, user_id))
        return participant.participant.admin_rights is not None
    except:
        return False

async def is_member(user_id):
    """Check if user is a member of the group."""
    try:
        await client(GetParticipantRequest(TARGET_GROUP, user_id))
        return True
    except:
        return False

async def mute_user(user_id):
    """Mute a VC participant."""
    try:
        await client(ToggleGroupCallParticipant(
            call=TARGET_GROUP,
            participant=user_id,
            muted=True
        ))
        print(f"[Muted] User {user_id}")
    except Exception as e:
        print(f"[Mute Failed] {user_id}: {e}")

# ====== GHOST MODE FUNCTIONS ======
async def ghost_mute_user(user_id):
    """Mute invisible user in VC fast."""
    await mute_user(user_id)
    await asyncio.sleep(0.5)  # leave VC if needed

# ====== AUTO-MUTE LOOP (Always Monitoring) ======
async def monitor_vc():
    while True:
        participants = await get_vc_participants()
        for user in participants:
            if not await is_admin(user.id):
                # Rule 1: Not in group → mute
                # Rule 2: Video on → mute
                if not await is_member(user.id) or getattr(user, "video", False):
                    await ghost_mute_user(user.id)
        await asyncio.sleep(2)  # check VC every 2 seconds

# ====== MAIN ======
async def main():
    print("🚀 Mega Ultra Elite Ghost VC Bot Running")
    async with client:
        await monitor_vc()

# ====== RUN ======
if __name__ == "__main__":
    asyncio.run(main())