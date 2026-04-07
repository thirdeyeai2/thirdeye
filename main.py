import asyncio
import os
from datetime import datetime
from pyrogram import Client
from pyrogram.raw.functions.phone import GetGroupCall, EditGroupCallParticipant

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = int(os.getenv("GROUP_ID"))

VC_CHECK_INTERVAL = 2   # stable (don't use 1s for now)

# ================= APP ====================
app = Client("vcghost_final", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

muted_users = set()
peer = None  # global peer

# ----------------- MUTE FUNCTION ----------------
async def mute_user(call, user_id, mute=True):
    try:
        await app.invoke(EditGroupCallParticipant(
            call=call,
            participant=user_id,
            muted=mute
        ))
        print(f"{'Muted' if mute else 'Unmuted'} {user_id}")
    except Exception as e:
        print(f"⚠️ Mute error {user_id}: {e}")

# ----------------- MAIN LOGIC ------------------
async def main():
    global peer

    print("🚀 Starting Ghost VC Bot...")

    await app.start()

    # ✅ Proper peer resolve (FIXED)
    peer = await app.resolve_peer(GROUP_ID)

    print("✅ Connected & Peer resolved")

    while True:
        try:
            # ✅ Get VC
            group_call = await app.invoke(GetGroupCall(peer=peer))
            participants = getattr(group_call, "participants", [])

            for p in participants:
                user_id = p.user_id

                try:
                    member = await app.get_chat_member(GROUP_ID, user_id)
                except:
                    continue

                # ✅ Admin skip
                if member.status in ["administrator", "creator"]:
                    continue

                # ✅ Non-member mute
                if not member.is_member:
                    if user_id not in muted_users:
                        await mute_user(group_call, user_id, True)
                        muted_users.add(user_id)
                    continue

                # ✅ Video mute
                if getattr(p, "video_enabled", False):
                    if user_id not in muted_users:
                        await mute_user(group_call, user_id, True)
                        muted_users.add(user_id)
                    continue

                # ✅ Auto unmute
                if user_id in muted_users and member.is_member:
                    await mute_user(group_call, user_id, False)
                    muted_users.remove(user_id)

        except Exception as e:
            print(f"⚠️ Loop error: {e}")

        await asyncio.sleep(VC_CHECK_INTERVAL)

# ----------------- RUN -------------------------
if __name__ == "__main__":
    asyncio.run(main())