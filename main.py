import asyncio
import os
import time
from pyrogram import Client
from pyrogram.raw.functions.phone import GetGroupCall, EditGroupCallParticipant

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = int(os.getenv("GROUP_ID"))

VC_CHECK_INTERVAL = 0.5  # stealth interval
muted_users = set()
app = Client("vcghost_elite", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

async def mute_user(call, user_id, mute=True):
    try:
        await app.invoke(EditGroupCallParticipant(call=call, participant=user_id, muted=mute))
        print(f"{time.strftime('%H:%M:%S')} | {'Muted' if mute else 'Unmuted'} {user_id}")
    except Exception as e:
        print(f"⚠️ Mute error {user_id}: {e}")

async def ultra_vc_loop():
    while True:
        try:
            peer = await app.resolve_peer(GROUP_ID)
            group_call = await app.invoke(GetGroupCall(peer=peer))
            participants = getattr(group_call, "participants", [])

            for p in participants:
                user_id = p.user_id
                try:
                    member = await app.get_chat_member(GROUP_ID, user_id)
                except:
                    continue

                # Admin/creator skip
                if member.status in ["administrator", "creator"]:
                    continue

                # Non-member or video -> mute
                if not member.is_member or getattr(p, "video_enabled", False):
                    if user_id not in muted_users:
                        await mute_user(group_call, user_id, True)
                        muted_users.add(user_id)

                # Auto unmute
                elif user_id in muted_users and member.is_member:
                    await mute_user(group_call, user_id, False)
                    muted_users.remove(user_id)

            # ultra ghost cycle (stealth)
            await asyncio.sleep(VC_CHECK_INTERVAL)

        except Exception as e:
            print(f"⚠️ Ultra loop error: {e}")
            await asyncio.sleep(1)

async def main():
    while True:
        try:
            print("🚀 Starting Ultra V2 Elite Ghost VC Bot...")
            await app.start()
            print("✅ Connected, running elite ghost VC loop")
            await ultra_vc_loop()
        except Exception as e:
            # Handle [16] and reconnect
            if "msg_id is too low" in str(e):
                print("⚠️ Server time desync detected. Retrying in 5s...")
                await asyncio.sleep(5)
                continue
            print(f"🔥 Fatal error: {e}, restarting in 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())