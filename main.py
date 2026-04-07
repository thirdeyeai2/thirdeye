import os
import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import InputPeerChannel

# ===== ENV VARIABLES =====
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME", "elite_userbot")
VC_CHANNELS = [int(ch) for ch in os.getenv("VC_CHANNELS", "").split(",") if ch]
GHOST_CHECK_INTERVAL = int(os.getenv("GHOST_CHECK_INTERVAL", 3))  # seconds

# ===== TELETHON CLIENT =====
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

async def ghost_vc_monitor(channel_id):
    """Join VC invisibly & mute violators"""
    while True:
        try:
            # Join VC in invisible mode (silent join)
            await client(functions.phone.JoinGroupCallRequest(
                peer=InputPeerChannel(channel_id, 0),
                join_as=list(),  # empty = invisible
                muted=True
            ))

            print(f"👻 Ghost joined VC {channel_id} silently")

            # Monitor participants
            @client.on(events.Raw)
            async def handle_vc_event(event):
                for p in getattr(event, 'participants', []):
                    # Auto-mute non-members or video-on
                    if not getattr(p, 'is_member', False) or getattr(p, 'video', False):
                        await client(functions.phone.ToggleGroupCallParticipantRequest(
                            call=event.call,
                            participant=p.user_id,
                            muted=True
                        ))
                        print(f"🔕 Muted {p.user_id} in {channel_id}")

            await asyncio.sleep(GHOST_CHECK_INTERVAL)
        except Exception as e:
            print(f"⚠ Error in VC {channel_id}: {e}")
            await asyncio.sleep(5)

async def main():
    await client.start()
    print("✅ Elite Ghost VC Userbot running (Invisible Mode)")

    # Launch ghost monitors for all channels
    tasks = [ghost_vc_monitor(ch) for ch in VC_CHANNELS]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())