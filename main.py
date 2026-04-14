import config
import asyncio
import time
from aiohttp import web
from telethon import TelegramClient, events
from telethon.tl import types, functions
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# ==========================================
# SETUP
# ==========================================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

bot = TelegramClient('bot_session', config.API_ID, config.API_HASH, loop=loop)
assistant = TelegramClient(
    "assistant_session",
    config.API_ID,
    config.API_HASH,
    loop=loop,
    auto_reconnect=True,
    connection_retries=None,
    retry_delay=3,
    request_retries=5
)

assistant_id = None
bot_id = None
last_refresh = 0

active_calls = {}

# ==========================================
# SAFE ENTITY FETCH
# ==========================================
async def get_entity_safe(peer):
    try:
        return await assistant.get_input_entity(peer)
    except:
        try:
            if isinstance(peer, types.PeerUser):
                return await assistant.get_entity(int(peer.user_id))
            elif isinstance(peer, int):
                return await assistant.get_entity(peer)
        except Exception as e:
            print(f"[ENTITY ERROR] {e}")
            return None

# ==========================================
# REFRESH CACHE
# ==========================================
async def refresh_cache(call):
    global last_refresh

    if not call:
        return

    if time.time() - last_refresh > 5:
        try:
            await assistant(functions.phone.GetGroupParticipantsRequest(
                call=call,
                ids=[],
                sources=[],
                offset='',
                limit=100
            ))
            last_refresh = time.time()
            print("[CACHE] VC participants refreshed")
        except Exception as e:
            print(f"[CACHE ERROR] {e}")

# ==========================================
# SAFE MUTE / UNMUTE
# ==========================================
async def safe_edit(call, peer, mute=True):
    if not call:
        return

    try:
        await refresh_cache(call)

        entity = await get_entity_safe(peer)
        if not entity:
            return

        await assistant(functions.phone.EditGroupCallParticipantRequest(
            call=call,
            participant=entity,
            muted=mute
        ))

        print(f"[{'MUTED' if mute else 'UNMUTED'}] {peer}")

    except FloodWaitError as e:
        print(f"[FLOOD] Wait {e.seconds}s")
        await asyncio.sleep(e.seconds)
        return await safe_edit(call, peer, mute)

    except Exception as e:
        print(f"[ERROR] Edit failed: {e}")

# ==========================================
# VC HANDLER
# ==========================================
@assistant.on(events.Raw(types.UpdateGroupCallParticipants))
async def vc_join_handler(event):
    call = event.call

    active_calls[str(config.GROUP_ID)] = call

    for participant in event.participants:
        if participant.left:
            continue

        peer_obj = participant.peer

        # ===== CHANNEL AUTO MUTE =====
        if isinstance(peer_obj, types.PeerChannel):
            print(f"[CHANNEL] {peer_obj.channel_id} → Muting")

            try:
                await assistant(functions.phone.EditGroupCallParticipantRequest(
                    call=call,
                    participant=peer_obj,
                    muted=True
                ))
                print(f"[SUCCESS] Channel muted")

            except Exception as e:
                print(f"[ERROR] Channel mute failed: {e}")

            continue

        # ===== USER =====
        if isinstance(peer_obj, types.PeerUser):
            user_id = peer_obj.user_id

            if user_id in [assistant_id, bot_id]:
                continue

            # 🔍 CHECK ADMIN
            is_admin = False
            try:
                p = await assistant(functions.channels.GetParticipantRequest(
                    channel=config.GROUP_ID,
                    participant=user_id
                ))

                if isinstance(p.participant, (
                    types.ChannelParticipantAdmin,
                    types.ChannelParticipantCreator
                )):
                    is_admin = True

            except:
                print(f"[INTRUDER] {user_id} → Muting")
                await safe_edit(call, peer_obj, True)
                continue

            # 🎥 VIDEO / SCREEN SHARE CHECK
            video_on = getattr(participant, "video", False)
            screen_on = getattr(participant, "presentation", False)

            if (video_on or screen_on) and not is_admin:
                print(f"[MEDIA BLOCK] {user_id} → Video/Screen ON → Muting")
                await safe_edit(call, peer_obj, True)
                continue

            print(f"[OK] {user_id} is member")

# ==========================================
# WEB SERVER (KEEP ALIVE)
# ==========================================
async def web_server():
    async def handle(request):
        return web.Response(text="VC Bot Running ✅")

    app = web.Application()
    app.add_routes([web.get('/', handle)])

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, '0.0.0.0', config.PORT)
    await site.start()

# ==========================================
# START
# ==========================================
async def main():
    global assistant_id, bot_id

    await bot.start(bot_token=config.BOT_TOKEN)
    bot_id = (await bot.get_me()).id
    print("Bot started")

    await assistant.start()
    assistant_id = (await assistant.get_me()).id
    print("Assistant started")

    await web_server()

    print("🛡️ VC AUTO CONTROL SYSTEM ACTIVE 🛡️")

    await asyncio.gather(
        bot.run_until_disconnected(),
        assistant.run_until_disconnected()
    )

# ==========================================
# ENTRY
# ==========================================
if __name__ == "__main__":
    loop.run_until_complete(main())