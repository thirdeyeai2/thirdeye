import asyncio
import os
from pyrogram import Client
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.phone import GetGroupCall, EditGroupCallParticipant
from pyrogram.raw.types import InputGroupCall

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = int(os.getenv("GROUP_ID"))

CHECK_INTERVAL = 0.5  # ultra-fast, safe for V3

# ================= APP ====================
app = Client("ultra_v3_ghost", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
muted_users = set()

# ----------------- MUTE FUNCTION ----------------
async def mute_user(call, user_id, mute=True):
    try:
        await app.invoke(EditGroupCallParticipant(
            call=call,
            participant=user_id,
            muted=mute
        ))
        print(f"{'Muted' if mute else 'Unmuted'} user: {user_id}")
    except Exception as e:
        print(f"⚠️ Mute error {user_id}: {e}")

# ----------------- FETCH VC ----------------
async def get_group_call():
    try:
        full_chat = await app.invoke(
            GetFullChannel(channel=await app.resolve_peer(GROUP_ID))
        )

        call = full_chat.full_chat.call
        if not call:
            return None

        group_call = await app.invoke(
            GetGroupCall(
                call=InputGroupCall(
                    id=call.id,
                    access_hash=call.access_hash
                )
            )
        )
        return group_call

    except Exception as e:
        print(f"⚠️ Get VC error: {e}")
        return None

# ----------------- MAIN LOOP ----------------
async def ultra_loop():
    print("🚀 Ultra V3 God Mode Ghost VC running...")
    await app.start()

    while True:
        try:
            group_call = await get_group_call()
            if not group_call or not hasattr(group_call, "participants"):
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            for p in group_call.participants:
                user_id = p.user_id
                # fetch member info
                try:
                    member = await app.get_chat_member(GROUP_ID, user_id)
                except:
                    continue

                # skip admins/creators
                if member.status in ["administrator", "creator"]:
                    continue

                # mute non-members
                if not member.is_member:
                    if user_id not in muted_users:
                        await mute_user(group_call, user_id, True)
                        muted_users.add(user_id)
                    continue

                # mute if video enabled
                if getattr(p, "video_enabled", False):
                    if user_id not in muted_users:
                        await mute_user(group_call, user_id, True)
                        muted_users.add(user_id)
                    continue

                # auto unmute when joining
                if user_id in muted_users and member.is_member:
                    await mute_user(group_call, user_id, False)
                    muted_users.remove(user_id)

        except Exception as e:
            print(f"⚠️ Ultra loop error: {e}")

        await asyncio.sleep(CHECK_INTERVAL)

# ----------------- RUN ----------------
if __name__ == "__main__":
    asyncio.run(ultra_loop())