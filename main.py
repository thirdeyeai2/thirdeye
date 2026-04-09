import asyncio
import os
from pyrogram import Client
from pyrogram.raw.functions.phone import (
    GetGroupCall,
    JoinGroupCall,
    EditGroupCallParticipant
)
from pyrogram.raw.types import InputGroupCall, DataJSON

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = os.getenv("GROUP_ID")

JOIN_DELAY = 12
LOOP_DELAY = 1  # safe fast loop

app = Client(
    "ultra_v5_final",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    no_updates=True
)

vc_joined = False
joining = False
muted_users = set()

def log(msg):
    print(msg)

# 🔍 Get VC
async def get_vc():
    try:
        chat = await app.get_chat(GROUP_ID)
        full = await app.invoke(
            GetGroupCall(
                call=InputGroupCall(id=chat.id, access_hash=0),
                limit=100
            )
        )
        return full
    except:
        return None

# 🔌 Join VC safely
async def join_vc(vc):
    global vc_joined, joining
    if vc_joined or joining:
        return

    joining = True
    log("⏳ Waiting before VC join...")
    await asyncio.sleep(JOIN_DELAY)

    try:
        await app.invoke(
            JoinGroupCall(
                call=vc.call,
                join_as=(await app.get_me()).id,
                muted=True,
                video_stopped=True,
                params=DataJSON(data='{"U":"1"}')
            )
        )
        vc_joined = True
        log("✅ Joined VC")
    except Exception as e:
        log(f"⚠️ Join error: {e}")

    joining = False

# 🔇 Mute / Unmute
async def mute_user(vc, user_id, state=True):
    try:
        await app.invoke(
            EditGroupCallParticipant(
                call=vc.call,
                participant=user_id,
                muted=state
            )
        )
        if state:
            muted_users.add(user_id)
        else:
            muted_users.discard(user_id)

        log(f"{'🔇 Muted' if state else '🔊 Unmuted'} {user_id}")

    except Exception as e:
        log(f"⚠️ Mute error {user_id}: {e}")

# 👑 Check admin
async def is_admin(user_id):
    try:
        member = await app.get_chat_member(GROUP_ID, user_id)
        return member.status in ("administrator", "creator")
    except:
        return False

# 👥 Check group member
async def is_member(user_id):
    try:
        member = await app.get_chat_member(GROUP_ID, user_id)
        return member.status not in ("left", "kicked")
    except:
        return False

# 🚀 Main loop
async def main():
    global vc_joined

    await app.start()
    log("🚀 ULTRA V5 FINAL STARTED")

    while True:
        vc = await get_vc()

        if not vc:
            vc_joined = False
            await asyncio.sleep(LOOP_DELAY)
            continue

        await join_vc(vc)

        if not vc_joined:
            await asyncio.sleep(LOOP_DELAY)
            continue

        try:
            for p in vc.participants:
                user_id = getattr(p.peer, "user_id", None)

                # 📡 Channel / anonymous accounts
                if not user_id:
                    continue

                # 👑 Skip admins
                if await is_admin(user_id):
                    continue

                # ❌ Not in group → mute
                if not await is_member(user_id):
                    if user_id not in muted_users:
                        await mute_user(vc, user_id, True)
                    continue

                # 🔄 Auto unmute if joined group
                if user_id in muted_users:
                    await mute_user(vc, user_id, False)

                # 🎥 Video ON → mute
                if getattr(p, "video", False):
                    await mute_user(vc, user_id, True)

        except Exception as e:
            log(f"⚠️ Loop error: {e}")

        await asyncio.sleep(LOOP_DELAY)

if __name__ == "__main__":
    asyncio.run(main())