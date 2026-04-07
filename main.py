import asyncio
from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsAdmins
from telethon.tl.functions.phone import GetGroupCallRequest, ToggleGroupCallParticipant

# ---------------- CONFIG ----------------
API_ID = YOUR_API_ID
API_HASH = 'YOUR_API_HASH'
SESSION = 'YOUR_SESSION_STRING'
GROUP_ID = -1001234567890  # your main group id
CHECK_INTERVAL = 2  # seconds

# ---------------- CLIENT ----------------
client = TelegramClient(SESSION, API_ID, API_HASH)
muted_users = set()  # track muted users

# ---------------- HELPER FUNCTIONS ----------------
async def is_admin(user_id):
    admins = await client.get_participants(GROUP_ID, filter=ChannelParticipantsAdmins)
    return user_id in [a.id for a in admins]

async def mute_user(vc, user_id):
    try:
        await client(ToggleGroupCallParticipant(
            call=vc,
            participant=user_id,
            muted=True
        ))
        muted_users.add(user_id)
        print(f"Muted user: {user_id}")
    except Exception as e:
        print(f"Error muting {user_id}: {e}")

async def unmute_user(vc, user_id):
    try:
        await client(ToggleGroupCallParticipant(
            call=vc,
            participant=user_id,
            muted=False
        ))
        if user_id in muted_users:
            muted_users.remove(user_id)
        print(f"Unmuted user: {user_id}")
    except Exception as e:
        print(f"Error unmuting {user_id}: {e}")

async def get_vc():
    try:
        vc = await client(GetGroupCallRequest(
            peer=GROUP_ID,
            limit=100
        ))
        return vc
    except Exception as e:
        print("Join VC Error:", e)
        return None

# ---------------- EVENTS ----------------
@client.on(events.ChatAction)
async def auto_unmute(event):
    # If someone joins the group and was muted in VC → unmute them
    if event.user_added or event.user_joined:
        user_id = event.user_id
        if user_id in muted_users:
            vc = await get_vc()
            if vc:
                await unmute_user(vc, user_id)

# ---------------- MONITORING LOOP ----------------
async def monitor_vc():
    while True:
        vc = await get_vc()
        if vc:
            participants = vc.participants
            for p in participants:
                # skip admins
                if await is_admin(p.user_id):
                    continue
                # mute if video on
                if getattr(p, 'video', False):
                    await mute_user(vc, p.user_id)
                # mute if channel account
                if getattr(p, 'peer', None) and hasattr(p.peer, 'channel_id'):
                    await mute_user(vc, p.user_id)
                # mute if not member
                try:
                    member = await client.get_entity(p.user_id)
                    if member not in await client.get_participants(GROUP_ID):
                        await mute_user(vc, p.user_id)
                except:
                    await mute_user(vc, p.user_id)
        await asyncio.sleep(CHECK_INTERVAL)

# ---------------- MAIN ----------------
async def main():
    print("🚀 MEGA VC GHOST + AUTO-UNMUTE SYSTEM RUNNING")
    await client.start()
    await monitor_vc()  # infinite loop

if __name__ == "__main__":
    asyncio.run(main())