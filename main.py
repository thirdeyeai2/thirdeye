import asyncio
import os
from pyrogram import Client, errors
from pyrogram.raw.functions.phone import GetGroupCall, EditGroupCallParticipant

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
GROUP_ID = int(os.getenv("GROUP_ID"))

VC_CHECK_INTERVAL = 2   # 2s is stable
GHOST_LEAVE_DELAY = 0.5 # 0.5s ghost leave

# ================= APP ====================
app = Client(
    "vcghost_ultra",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

muted_users = set()
peer = None

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

# ----------------- GHOST JOIN/LEAVE ----------------
async def ghost_join_leave():
    try:
        # Join VC (silent / invisible)
        group_call = await app.invoke(GetGroupCall(peer=peer))
        print("👻 Ghost joined VC")
        await asyncio.sleep(GHOST_LEAVE_DELAY)
        # Leave VC instantly
        await app.invoke(EditGroupCallParticipant(call=group_call, participant="me", muted=True))
        print("👻 Ghost left VC")
    except Exception as e:
        print(f"⚠️ Ghost join/leave error: {e}")

# ----------------- MAIN VC LOOP ------------------
async def vc_monitor_loop():
    while True:
        try:
            group_call = await app.invoke(GetGroupCall(peer=peer))
            participants = getattr(group_call, "participants", [])

            for p in participants:
                user_id = p.user_id

                # Get member info safely
                try:
                    member = await app.get_chat_member(GROUP_ID, user_id)
                except errors.UserNotParticipant:
                    member = None

                # ✅ Admin skip
                if member and member.status in ["administrator", "creator"]:
                    continue

                # ✅ Non-member mute
                if not member or not getattr(member, "is_member", False):
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
                if user_id in muted_users and member and member.is_member:
                    await mute_user(group_call, user_id, False)
                    muted_users.remove(user_id)

                # ✅ Channel account mute
                if getattr(p, "peer_type", None) == "channel":
                    if user_id not in muted_users:
                        await mute_user(group_call, user_id, True)
                        muted_users.add(user_id)

        except Exception as e:
            print(f"⚠️ VC loop error: {e}")

        await asyncio.sleep(VC_CHECK_INTERVAL)

# ----------------- RUN -------------------------
async def main():
    global peer
    print("🚀 Starting Ultra Ghost VC Bot...")

    await app.start(sync_time=True)

    # Resolve peer
    try:
        peer = await app.resolve_peer(GROUP_ID)
        print(f"✅ Peer resolved: {peer}")
    except Exception as e:
        print(f"⚠️ Peer resolve failed: {e}")
        return

    # Start ghost join/leave task
    asyncio.create_task(ghost_join_leave())
    # Start VC monitor
    await vc_monitor_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot stopped manually")
    except Exception as e:
        print(f"🔥 Fatal error: {e}")