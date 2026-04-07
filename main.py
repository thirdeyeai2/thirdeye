import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.functions.phone import GetGroupCallRequest, ToggleGroupCallParticipant
from telethon.tl.types import PeerChannel, ChannelParticipantAdmin

# ===== ENV VARIABLES =====
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
TARGET_GROUP = int(os.getenv("TARGET_GROUP"))

# ===== CLIENT SETUP =====
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ====== HELPER FUNCTIONS ======
async def is_admin(user_id: int) -> bool:
    try:
        participant = await client(GetParticipantRequest(TARGET_GROUP, user_id))
        return isinstance(participant.participant, ChannelParticipantAdmin)
    except:
        return False

async def is_member(user_id: int) -> bool:
    try:
        await client(GetParticipantRequest(TARGET_GROUP, user_id))
        return True
    except:
        return False

async def mute_user(call, user_id: int):
    try:
        await client(ToggleGroupCallParticipant(
            call=call,
            participant=user_id,
            muted=True
        ))
        print(f"[MUTED] User {user_id}")
    except Exception as e:
        print(f"[MUTE FAILED] {user_id}: {e}")

async def unmute_user(call, user_id: int):
    try:
        await client(ToggleGroupCallParticipant(
            call=call,
            participant=user_id,
            muted=False
        ))
        print(f"[UNMUTED] User {user_id}")
    except Exception as e:
        print(f"[UNMUTE FAILED] {user_id}: {e}")

# ====== AUTO-UNMUTE HANDLER =====
@client.on(events.ChatAction)
async def handle_join(event):
    if event.user_joined or event.user_added:
        user_id = event.user_id
        # Auto unmute if user joins group
        try:
            call = await client(GetGroupCallRequest(peer=TARGET_GROUP, limit=100))
            await unmute_user(call, user_id)
        except Exception as e:
            print(f"[AUTO UNMUTE ERROR] {user_id}: {e}")

# ===== VC MONITOR LOOP =====
async def monitor_vc():
    while True:
        try:
            call = await client(GetGroupCallRequest(peer=TARGET_GROUP, limit=100))
            participants = call.participants
            for user in participants:
                uid = user.user_id
                if await is_admin(uid):
                    continue  # Skip admins
                # Non-member → mute
                if not await is_member(uid):
                    await mute_user(call, uid)
                # Video on → mute
                if getattr(user, "video", False):
                    await mute_user(call, uid)
                # Channel ID → mute
                if str(uid).startswith("-100"):
                    await mute_user(call, uid)
        except Exception as e:
            print(f"[VC ERROR] {e}")
        await asyncio.sleep(2)  # checks every 2 seconds

# ===== MAIN =====
async def main():
    print("🚀 MEGA ULTRA GHOST VC USERBOT RUNNING")
    async with client:
        await monitor_vc()

if __name__ == "__main__":
    asyncio.run(main())