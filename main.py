import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.functions.phone import GetGroupCallRequest, GetGroupCallParticipantsRequest, ToggleGroupCallParticipant

# ====== ENV VARIABLES ======
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")  # Invisible StringSession
TARGET_GROUP = int(os.getenv("TARGET_GROUP"))  # Group/Channel ID to monitor
CHECK_INTERVAL = float(os.getenv("CHECK_INTERVAL", 0.5))  # 0.5 sec for ultra fast

# ====== CLIENT SETUP ======
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ====== HELPERS ======
async def is_admin(user_id):
    try:
        participant = await client(GetParticipantRequest(TARGET_GROUP, user_id))
        return getattr(participant.participant, "admin_rights", None) is not None
    except:
        return False

async def is_member(user_id):
    try:
        await client(GetParticipantRequest(TARGET_GROUP, user_id))
        return True
    except:
        return False

async def get_vc_call():
    try:
        call = await client(GetGroupCallRequest(TARGET_GROUP))
        return call.call
    except Exception as e:
        print(f"[VC ERROR] {e}")
        return None

async def get_vc_participants(call):
    try:
        result = await client(GetGroupCallParticipantsRequest(call=call, limit=100))
        return result.participants
    except Exception as e:
        print(f"[VC PARTICIPANTS ERROR] {e}")
        return []

async def mute_user(call, user_id):
    try:
        await client(ToggleGroupCallParticipant(call=call, participant=user_id, muted=True))
        print(f"[MUTED] {user_id}")
    except Exception as e:
        print(f"[MUTE FAILED] {user_id}: {e}")

async def ghost_mute(call, user_id):
    await mute_user(call, user_id)
    await asyncio.sleep(0.1)  # ultra stealth leave (optional)

# ====== MEGA MONITOR LOOP ======
async def monitor_vc():
    """Always-on VC monitoring, Mega Ultra Elite version."""
    seen_users = set()  # Track new joiners for instant action
    while True:
        call = await get_vc_call()
        if call:
            participants = await get_vc_participants(call)
            for user in participants:
                user_id = user.peer.user_id
                # Skip admins
                if await is_admin(user_id):
                    continue

                # Ultra rules:
                # 1️⃣ Not a group member → mute instantly
                if not await is_member(user_id):
                    await ghost_mute(call, user_id)
                    continue

                # 2️⃣ Video ON → mute instantly
                if getattr(user, "video", False):
                    await ghost_mute(call, user_id)
                    continue

                # 3️⃣ Instant reaction for new joiners
                if user_id not in seen_users:
                    seen_users.add(user_id)
                    await ghost_mute(call, user_id)
        await asyncio.sleep(CHECK_INTERVAL)

# ====== MAIN ======
async def main():
    print("🚀 MEGA ULTRA ELITE Ghost VC Bot Running! (Admins Safe, Instant Mute, Always Monitoring)")
    async with client:
        await monitor_vc()

# ====== RUN ======
if __name__ == "__main__":
    asyncio.run(main())