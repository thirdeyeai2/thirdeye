import asyncio
import os
import time
from datetime import datetime
from pyrogram import Client
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.phone import GetGroupCall, JoinGroupCall, EditGroupCallParticipant
from pyrogram.raw.types import InputGroupCall, DataJSON

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = os.getenv("GROUP_ID")  # @username or -100id

CHECK_INTERVAL = 2
JOIN_DELAY = 12  # 🔥 important for SSRC fix

# ================= APP ====================
app = Client(
    "ultra_v5_final",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    no_updates=True
)

# ================= STATE ==================
vc_joined = False
joining = False
JOIN_AS = None
muted_users = set()

# ================= LOGGER =================
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ================= GET VC =================
async def get_vc():
    try:
        peer = await app.resolve_peer(GROUP_ID)
        full = await app.invoke(GetFullChannel(channel=peer))
        call = getattr(full.full_chat, "call", None)
        if not call:
            return None

        return await app.invoke(
            GetGroupCall(
                call=InputGroupCall(id=call.id, access_hash=call.access_hash),
                limit=100
            )
        )
    except Exception as e:
        log(f"⚠️ VC fetch error: {e}")
        return None

# ================= SAFE JOIN =================
async def join_vc(vc):
    global vc_joined, joining

    if vc_joined or joining:
        return

    joining = True
    log("⏳ Waiting before VC join (SSRC protection)...")
    await asyncio.sleep(JOIN_DELAY)

    try:
        await app.invoke(
            JoinGroupCall(
                call=InputGroupCall(id=vc.call.id, vc.call.access_hash),
                join_as=JOIN_AS,
                muted=True,
                video_stopped=True,
                params=DataJSON(data='{"U":"1"}')
            )
        )
        vc_joined = True
        log("✅ Joined VC successfully")
    except Exception as e:
        log(f"⚠️ Join skipped: {e}")

    joining = False

# ================= MEMBER CHECK =================
async def is_member(user_id):
    try:
        m = await app.get_chat_member(GROUP_ID, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

# ================= MUTE =================
async def mute(vc, user_id, state=True):
    try:
        await app.invoke(
            EditGroupCallParticipant(
                call=vc.call,
                participant=user_id,
                muted=state
            )
        )
        log(f"{'🔇 Muted' if state else '🔊 Unmuted'} {user_id}")
    except Exception as e:
        log(f"⚠️ Mute error {user_id}: {e}")

# ================= MAIN LOOP =================
async def main():
    global JOIN_AS, vc_joined

    log("🚀 ULTRA V5 FINAL STARTED")
    await app.start()

    me = await app.get_me()
    JOIN_AS = await app.resolve_peer(me.id)

    # Join group (safe)
    try:
        await app.join_chat(GROUP_ID)
    except:
        pass

    while True:
        try:
            vc = await get_vc()

            if not vc:
                vc_joined = False
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            await join_vc(vc)

            if not vc_joined:
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            current_users = set()

            for p in vc.participants:
                part = getattr(p, "participant", None)
                if not part or not hasattr(part, "user_id"):
                    continue

                uid = part.user_id
                current_users.add(uid)

                valid = await is_member(uid)
                video = getattr(part, "video_enabled", False)

                # 🔴 Non-member mute
                if not valid:
                    if uid not in muted_users:
                        await mute(vc, uid, True)
                        muted_users.add(uid)
                    continue

                # 🎥 Video ON mute
                if video:
                    if uid not in muted_users:
                        await mute(vc, uid, True)
                        muted_users.add(uid)
                    continue

                # 🔊 Auto unmute
                if uid in muted_users:
                    await mute(vc, uid, False)
                    muted_users.remove(uid)

            # cleanup
            muted_users.intersection_update(current_users)

        except Exception as e:
            log(f"⚠️ Loop error: {e}")

        await asyncio.sleep(CHECK_INTERVAL)

# ================= RUN =================
if __name__ == "__main__":
    asyncio.run(main())