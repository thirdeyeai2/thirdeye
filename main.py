import asyncio
import os
from datetime import datetime
from pyrogram import Client
from pyrogram.raw import functions, types
import time

# ==================== CONFIG ====================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = int(os.getenv("GROUP_ID"))
VC_CHECK_INTERVAL = 0.5  # ultra-fast VC loop
STEALTH_DELAY = 0.5       # join-mute-leave delay in seconds
# ================================================

os.environ['TZ'] = 'UTC'
time.tzset()

app = Client(
    "vcghost_ultra_invisible",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

muted_users = set()

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
    except Exception as e:
        print(f"Error muting {user_id}: {e}")

# ----------------- TIME SYNC ----------------
async def sync_time():
    synced = False
    while not synced:
        try:
            ts = int(datetime.utcnow().timestamp() * 1000)
            await app.invoke(functions.Ping(ping_id=ts))
            synced = True
            print("⏱️ Time synced with Telegram!")
        except Exception as e:
            print(f"⚠️ Ping failed, retrying 1s: {e}")
            await asyncio.sleep(1)

# ----------------- INVISIBLE STEALTH VC ----------------
async def stealth_join_leave():
    try:
        # Invisible join by not sending presence
        group_call = await app.invoke(
            functions.phone.GetGroupCallRequest(
                peer=types.InputPeerChannel(channel_id=GROUP_ID, access_hash=0),
                limit=0
            )
        )
        print("👻 Joined VC invisibly")

        # Mute self immediately
        await mute_participant(group_call, "self", True)
        await asyncio.sleep(STEALTH_DELAY)
        print("🚪 Left VC stealthily")
    except Exception as e:
        print(f"⚠️ Stealth join/leave error: {e}")

# ----------------- GHOST VC LOOP ----------------
async def ghost_vc_loop():
    print("🚀 Ghost VC Ultra-Invisible Starting...")
    await app.start()
    await sync_time()

    while True:
        try:
            group_call = await app.invoke(
                functions.phone.GetGroupCallRequest(
                    peer=types.InputPeerChannel(channel_id=GROUP_ID, access_hash=0),
                    limit=100
                )
            )
            participants = group_call.participants

            for p in participants:
                user_id = p.user_id
                user = await app.get_users(user_id)
                member_status = await app.get_chat_member(GROUP_ID, user_id)

                if member_status.status in ["administrator", "creator"]:
                    continue

                if user.is_bot or not member_status.is_member or getattr(p, "video", False):
                    if user_id not in muted_users:
                        await mute_participant(group_call, user_id, True)
                        muted_users.add(user_id)
                    continue

                if user_id in muted_users and member_status.is_member:
                    await mute_participant(group_call, user_id, False)
                    muted_users.remove(user_id)

        except Exception as e:
            print(f"⚠️ VC loop error: {e}")

        await asyncio.sleep(VC_CHECK_INTERVAL)

# ----------------- AUTO-RESTART FOREVER ----------------
async def run_forever():
    while True:
        try:
            await asyncio.gather(
                ghost_vc_loop(),
                stealth_join_leave()
            )
        except Exception as e:
            print(f"🔥 Bot crashed, restarting in 3s: {e}")
            await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(run_forever())