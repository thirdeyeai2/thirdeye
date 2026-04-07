import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.phone import (
    GetGroupCallRequest,
    GetGroupCallParticipantsRequest,
    EditGroupCallParticipantRequest,
    JoinGroupCallRequest
)
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import InputPeerUser

# ===== ENV =====
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = int(os.getenv("TARGET_GROUP"))

CHECK_DELAY = 1

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

muted_cache = set()

# ===== HELPERS =====
async def is_admin(user_id):
    try:
        p = await client(GetParticipantRequest(GROUP_ID, user_id))
        return getattr(p.participant, "admin_rights", None) is not None
    except:
        return False

async def is_member(user_id):
    try:
        await client(GetParticipantRequest(GROUP_ID, user_id))
        return True
    except:
        return False

async def vc_mute(call, user_id):
    try:
        await client(EditGroupCallParticipantRequest(
            call=call,
            participant=InputPeerUser(user_id, 0),
            muted=True
        ))
        muted_cache.add(user_id)
        print(f"[MUTED] {user_id}")
    except Exception as e:
        print(f"[MUTE ERROR] {e}")

async def vc_unmute(call, user_id):
    try:
        await client(EditGroupCallParticipantRequest(
            call=call,
            participant=InputPeerUser(user_id, 0),
            muted=False
        ))
        muted_cache.discard(user_id)
        print(f"[UNMUTED] {user_id}")
    except Exception as e:
        print(f"[UNMUTE ERROR] {e}")

# ===== AUTO JOIN VC =====
async def join_vc():
    try:
        data = await client(GetGroupCallRequest(
            peer=GROUP_ID,
            limit=0
        ))
        call = data.call

        await client(JoinGroupCallRequest(
            call=call,
            join_as=GROUP_ID,
            params=b'{}'
        ))

        print("✅ Joined VC")
    except Exception as e:
        print("Join VC Error:", e)

# ===== MAIN LOOP =====
async def monitor():
    print("🚀 VC SYSTEM RUNNING")

    while True:
        try:
            data = await client(GetGroupCallRequest(
                peer=GROUP_ID,
                limit=0
            ))

            call = data.call

            participants = await client(GetGroupCallParticipantsRequest(
                call=call,
                limit=100
            ))

            for user in participants.participants:
                uid = user.user_id

                # Skip admins
                if await is_admin(uid):
                    continue

                # RULE 1: Not in group
                if not await is_member(uid):
                    if uid not in muted_cache:
                        await vc_mute(call, uid)
                    continue

                # RULE 2: Auto unmute
                if uid in muted_cache:
                    await vc_unmute(call, uid)

                # RULE 3: Video (limited detection)
                if getattr(user, "video", False):
                    if uid not in muted_cache:
                        await vc_mute(call, uid)

        except Exception as e:
            print("[ERROR]", e)

        await asyncio.sleep(CHECK_DELAY)

# ===== START =====
async def main():
    async with client:
        await join_vc()
        await monitor()

if __name__ == "__main__":
    asyncio.run(main())