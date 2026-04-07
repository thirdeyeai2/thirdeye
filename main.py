import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.phone import GetGroupCallRequest
from telethon.tl.functions.channels import GetParticipantRequest

# ====== ENV ======
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
TARGET_GROUP = int(os.getenv("TARGET_GROUP"))

# ====== CLIENT ======
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ====== CACHE ======
muted_users = set()

# ====== HELPERS ======
async def get_call():
    try:
        res = await client(GetGroupCallRequest(TARGET_GROUP))
        return res.call
    except:
        return None

async def get_vc_users(call):
    try:
        return await client.get_participants(call)
    except:
        return []

async def is_admin(user_id):
    try:
        p = await client(GetParticipantRequest(TARGET_GROUP, user_id))
        return getattr(p.participant, "admin_rights", None) is not None
    except:
        return False

async def is_member(user_id):
    try:
        await client(GetParticipantRequest(TARGET_GROUP, user_id))
        return True
    except:
        return False

# ====== ACTIONS ======
async def mute(user):
    try:
        await client.edit_permissions(TARGET_GROUP, user.id, send_messages=False)
        muted_users.add(user.id)
        print(f"[MUTED] {user.id}")
    except Exception as e:
        print(f"[MUTE FAIL] {user.id} -> {e}")

async def unmute(user):
    try:
        await client.edit_permissions(TARGET_GROUP, user.id, send_messages=True)
        muted_users.discard(user.id)
        print(f"[UNMUTED] {user.id}")
    except Exception as e:
        print(f"[UNMUTE FAIL] {user.id} -> {e}")

# ====== MAIN LOGIC ======
async def monitor():
    print("🚀 VC Ghost Controller Running...")

    while True:
        call = await get_call()

        if call:
            users = await get_vc_users(call)

            for user in users:
                uid = user.id

                # Skip admins
                if await is_admin(uid):
                    continue

                # Detect channel / bot
                is_channel = getattr(user, "broadcast", False) or getattr(user, "bot", False)

                member = await is_member(uid)
                video_on = getattr(user, "video", False)

                # ===== RULE 1: Not member → MUTE =====
                if not member:
                    if uid not in muted_users:
                        await mute(user)
                    continue

                # ===== RULE 2: Joined group → UNMUTE =====
                if member and uid in muted_users and not video_on:
                    await unmute(user)

                # ===== RULE 3: Video ON → MUTE =====
                if video_on:
                    if uid not in muted_users:
                        await mute(user)
                    continue

                # ===== RULE 4: Channel/Bot → MUTE =====
                if is_channel:
                    if uid not in muted_users:
                        await mute(user)
                    continue

        await asyncio.sleep(1)  # fast monitoring

# ====== START ======
async def main():
    async with client:
        await monitor()

if __name__ == "__main__":
    asyncio.run(main())