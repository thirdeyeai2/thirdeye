import asyncio
import os
from datetime import datetime
from pyrogram import Client
from pyrogram.raw import functions, types

# ==================== CONFIG ====================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = int(os.getenv("GROUP_ID"))
VC_CHECK_INTERVAL = 1  # stable + fast
# ================================================

app = Client(
    "vcghost_final",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

muted_users = set()

# ----------------- TIME SYNC ----------------
async def sync_time():
    try:
        ts = int(datetime.utcnow().timestamp() * 1000)
        await app.invoke(functions.Ping(ping_id=ts))
        print("⏱️ Time synced")
    except Exception as e:
        print(f"⚠️ Time sync error: {e}")

# ----------------- SAFE MUTE ----------------
async def mute_participant(call, user_id, mute=True):
    try:
        await app.invoke(
            functions.phone.EditGroupCallParticipant(
                call=call,
                participant=user_id,
                muted=mute
            )
        )
        print(f"{'🔇 Muted' if mute else '🔊 Unmuted'} {user_id}")
    except Exception as e:
        print(f"⚠️ Mute error {user_id}: {e}")

# ----------------- MAIN VC LOOP ----------------
async def vc_loop():
    print("🚀 VC Ghost Bot Started")

    await app.start()
    await sync_time()

    while True:
        try:
            group_call = await app.invoke(
                functions.phone.GetGroupCall(
                    peer=types.InputPeerChannel(
                        channel_id=GROUP_ID,
                        access_hash=0
                    )
                )
            )

            participants = getattr(group_call, "participants", [])

            for p in participants:
                try:
                    user_id = p.user_id
                    user = await app.get_users(user_id)
                    member = await app.get_chat_member(GROUP_ID, user_id)

                    # Skip admins
                    if member.status in ["administrator", "creator"]:
                        continue

                    # Mute conditions
                    should_mute = (
                        user.is_bot or
                        not member.is_member or
                        getattr(p, "video", False)
                    )

                    # MUTE
                    if should_mute:
                        if user_id not in muted_users:
                            await mute_participant(group_call, user_id, True)
                            muted_users.add(user_id)

                    # UNMUTE
                    else:
                        if user_id in muted_users:
                            await mute_participant(group_call, user_id, False)
                            muted_users.remove(user_id)

                except Exception as inner_error:
                    print(f"⚠️ User error: {inner_error}")

        except Exception as e:
            print(f"⚠️ VC fetch error: {e}")

        await asyncio.sleep(VC_CHECK_INTERVAL)

# ----------------- AUTO RESTART ----------------
async def run_forever():
    while True:
        try:
            await vc_loop()
        except Exception as e:
            print(f"🔥 Crash detected: {e}")
            print("♻️ Restarting in 5 seconds...")
            await asyncio.sleep(5)

# ----------------- START ----------------
if __name__ == "__main__":
    asyncio.run(run_forever())