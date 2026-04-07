import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.functions.phone import GetGroupCallRequest, ToggleGroupCallParticipant
from telethon.tl.types import ChannelParticipantsAdmins, InputPeerChannel

# ===== CONFIG =====
API_ID = 123456          # your api_id
API_HASH = 'your_api_hash'
SESSION_STRING = 'your_session_string'
GROUP_ID = -1001234567890  # group where VC is running

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ===== GLOBALS =====
monitoring = True
muted_users = set()
admin_ids = set()

async def fetch_admins():
    """Auto fetch all group admins"""
    global admin_ids
    admins = await client(GetParticipantsRequest(
        channel=GROUP_ID,
        filter=ChannelParticipantsAdmins(),
        offset=0,
        limit=100,
        hash=0
    ))
    admin_ids = {user.id for user in admins.users}
    print("Admins loaded:", admin_ids)

async def monitor_vc():
    """Continuously monitor VC participants"""
    await client.start()
    print("🚀 MEGA VC GHOST SYSTEM RUNNING")

    while monitoring:
        try:
            # Fetch VC participants
            vc = await client(GetGroupCallRequest(
                peer=InputPeerChannel(channel_id=GROUP_ID, access_hash=0),
                limit=50
            ))

            for user in vc.participants:
                user_id = user.user_id

                # Skip admins
                if user_id in admin_ids:
                    continue

                # Channel accounts / bots always muted
                if getattr(user, 'bot', False):
                    await client(ToggleGroupCallParticipant(
                        call=vc.call,
                        participant=user,
                        muted=True
                    ))
                    print(f"Muted channel/bot: {user_id}")
                    muted_users.add(user_id)
                    continue

                # Non-member auto-mute
                member = await client.get_permissions(GROUP_ID, user_id)
                if not member:
                    await client(ToggleGroupCallParticipant(
                        call=vc.call,
                        participant=user,
                        muted=True
                    ))
                    print(f"Muted non-member: {user_id}")
                    muted_users.add(user_id)
                    continue

                # Mute if user is on video
                if getattr(user, 'video', False):
                    await client(ToggleGroupCallParticipant(
                        call=vc.call,
                        participant=user,
                        muted=True
                    ))
                    print(f"Muted video user: {user_id}")
                    muted_users.add(user_id)

            # Auto unmute when muted users join the group
            for uid in list(muted_users):
                member = await client.get_permissions(GROUP_ID, uid)
                if member:
                    try:
                        await client(ToggleGroupCallParticipant(
                            call=vc.call,
                            participant=uid,
                            muted=False
                        ))
                        print(f"Unmuted user who joined group: {uid}")
                        muted_users.remove(uid)
                    except:
                        pass

        except Exception as e:
            print("Error monitoring VC:", e)

        await asyncio.sleep(2)  # 1–2 seconds loop

async def main():
    await fetch_admins()
    await monitor_vc()

client.loop.run_until_complete(main())