import os
import asyncio
from pyrogram import Client
from pyrogram.raw import functions, types

# ------------------- VARIABLES -------------------
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = int(os.getenv("GROUP_ID"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 2))  # default 2 sec

# ------------------- USERBOT INIT -------------------
app = Client(
    "vc_ghost_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# ------------------- HELPER FUNCTIONS -------------------
async def is_member(user_id):
    try:
        member = await app.get_chat_member(GROUP_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def is_admin(user_id):
    try:
        member = await app.get_chat_member(GROUP_ID, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False

async def mute_user(call, user_id):
    try:
        await app.send(
            functions.phone.EditGroupCallParticipant(
                call=types.InputGroupCall(id=call.id, access_hash=call.access_hash),
                participant=types.InputPeerUser(user_id=user_id),
                muted=True
            )
        )
        print(f"[MUTED] User: {user_id}")
    except Exception as e:
        print(f"[ERROR MUTE] {user_id}: {e}")

async def unmute_user(call, user_id):
    try:
        await app.send(
            functions.phone.EditGroupCallParticipant(
                call=types.InputGroupCall(id=call.id, access_hash=call.access_hash),
                participant=types.InputPeerUser(user_id=user_id),
                muted=False
            )
        )
        print(f"[UNMUTED] User: {user_id}")
    except Exception as e:
        print(f"[ERROR UNMUTE] {user_id}: {e}")

# ------------------- VC MONITOR -------------------
async def monitor_vc():
    async with app:
        print("🚀 MEGA VC GHOST SYSTEM RUNNING")
        while True:
            try:
                call = await app.send(functions.phone.GetGroupCall(peer=GROUP_ID))
                participants = call.participants.participants

                for p in participants:
                    user_id = p.user_id
                    # Admin exemption
                    if await is_admin(user_id):
                        continue

                    # Channel account mute
                    if isinstance(p.peer, types.InputPeerChannel):
                        await mute_user(call, user_id)
                        continue

                    # Non-member auto-mute
                    if not await is_member(user_id):
                        await mute_user(call, user_id)
                        continue

                    # Video detection mute
                    if getattr(p, "video_paused", None) is False:
                        await mute_user(call, user_id)
                        continue

                    # Auto unmute (member joined)
                    if await is_member(user_id):
                        await unmute_user(call, user_id)

            except Exception as e:
                print(f"[VC MONITOR ERROR] {e}")

            await asyncio.sleep(CHECK_INTERVAL)

# ------------------- RUN -------------------
asyncio.run(monitor_vc())