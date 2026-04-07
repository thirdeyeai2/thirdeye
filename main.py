import asyncio
import os
from datetime import datetime
from pyrogram import Client
from pyrogram.errors import RPCError
from pyrogram.raw import functions, types

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = int(os.getenv("GROUP_ID"))
VC_CHECK_INTERVAL = 0.5  # seconds

app = Client("vcghost", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
muted_users = set()

# ----------------- TIME SYNC -------------------
async def sync_time():
    synced = False
    while not synced:
        try:
            ts = int(datetime.utcnow().timestamp() * 1000)
            await app.invoke(functions.Ping(ping_id=ts))
            synced = True
            print("⏱️ Time synced successfully!")
        except RPCError as e:
            print(f"⚠️ Ping failed, retrying 1s: {e}")
            await asyncio.sleep(1)

# ----------------- MUTE FUNCTION ----------------
async def mute_participant(call, user_id, mute=True):
    try:
        await app.invoke(
            functions.phone.ToggleGroupCallParticipant(
                call=call,
                participant=user_id,
                muted=mute
            )
        )
        print(f"{'Muted' if mute else 'Unmuted'} user {user_id}")
    except RPCError as e:
        print(f"⚠️ Error muting/unmuting {user_id}: {e}")

# ----------------- GET ACTIVE VC -----------------
async def get_active_vc():
    try:
        chat = await app.get_chat(GROUP_ID)
        if not chat.has_active_call:
            return None
        call = types.InputGroupCall(
            id=chat.call.id,
            access_hash=chat.call.access_hash
        )
        return call
    except RPCError as e:
        print(f"⚠️ VC fetch error: {e}")
        return None

# ----------------- STEALTH JOIN / LEAVE -----------------
async def stealth_mute(user_id):
    """Join VC, mute user instantly, leave VC (0.5s)"""
    try:
        vc_call = await get_active_vc()
        if not vc_call:
            return
        await mute_participant(vc_call, user_id, True)
        await asyncio.sleep(0.5)  # leave instantly
    except Exception as e:
        print(f"⚠️ Stealth join/leave error: {e}")

# ----------------- MONITOR VC -------------------
async def monitor_vc():
    await app.start()
    print("🚀 Ghost VC Ultra-Invisible Starting...")
    await sync_time()

    while True:
        try:
            vc_call = await get_active_vc()
            if not vc_call:
                await asyncio.sleep(VC_CHECK_INTERVAL)
                continue

            participants = await app.invoke(functions.phone.GetGroupCall(call=vc_call, limit=100))
            for p in participants.participants:
                user_id = p.user_id
                user = await app.get_users(user_id)
                member_status = await app.get_chat_member(GROUP_ID, user_id)

                # Admins skip
                if member_status.status in ["administrator", "creator"]:
                    continue

                # Auto-mute bots/non-members/video
                if user.is_bot or not member_status.is_member or getattr(p, "video", False):
                    if user_id not in muted_users:
                        await stealth_mute(user_id)
                        muted_users.add(user_id)
                    continue

                # Auto-unmute if previously muted
                if user_id in muted_users and member_status.is_member:
                    await mute_participant(vc_call, user_id, False)
                    muted_users.remove(user_id)

        except Exception as e:
            print(f"⚠️ VC loop error: {e}")
            await asyncio.sleep(5)

        await asyncio.sleep(VC_CHECK_INTERVAL)

# ----------------- RUN BOT ----------------------
if __name__ == "__main__":
    while True:
        try:
            asyncio.run(monitor_vc())
        except Exception as e:
            print(f"🔥 Crash detected: {e}")
            print("♻️ Restarting in 5 seconds...")
            asyncio.run(asyncio.sleep(5))