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
    StringSession(config.SESSION_STRING),
    config.API_ID,
    config.API_HASH,
    loop=loop,
    connection_retries=None,
    retry_delay=2,
    auto_reconnect=True
)

assistant_id = None
bot_id = None
last_refresh = 0

active_calls = {}
muted_users = {}

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
# REFRESH CACHE (FAST)
# ==========================================
async def refresh_cache(call):
    global last_refresh

    if not call:
        return

    if time.time() - last_refresh > 2:  # ⚡ faster refresh
        try:
            await assistant(functions.phone.GetGroupParticipantsRequest(
                call=call,
                ids=[],
                sources=[],
                offset='',
                limit=100
            ))
            last_refresh = time.time()
        except Exception as e:
            print(f"[CACHE ERROR] {e}")

# ==========================================
# SAFE MUTE (ANTI-SPAM)
# ==========================================
async def safe_edit(call, peer, mute=True):
    if not call:
        return

    user_id = None

    if isinstance(peer, types.PeerUser):
        user_id = peer.user_id
    elif isinstance(peer, int):
        user_id = peer

    # 🔥 Anti duplicate
    if mute and user_id:
        now = time.time()

        if user_id in muted_users:
            if now - muted_users[user_id] < 3:  # ⚡ ultra fast cooldown
                return

        muted_users[user_id] = now

    try:
        entity = await get_entity_safe(peer)
        if not entity:
            return

        await assistant(functions.phone.EditGroupCallParticipantRequest(
            call=call,
            participant=entity,
            muted=mute
        ))

        print(f"[MUTED] {user_id}")

    except FloodWaitError as e:
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"[ERROR] {e}")

# ==========================================
# VC EVENT HANDLER
# ==========================================
@assistant.on(events.Raw(types.UpdateGroupCallParticipants))
async def vc_handler(event):
    call = event.call
    active_calls[str(config.GROUP_ID)] = call

    for participant in event.participants:
        if participant.left:
            continue

        peer = participant.peer

        # ===== CHANNEL =====
        if isinstance(peer, types.PeerChannel):
            try:
                entity = await assistant.get_input_entity(peer.channel_id)

                await assistant(functions.phone.EditGroupCallParticipantRequest(
                    call=call,
                    participant=entity,
                    muted=True
                ))

                print("[CHANNEL MUTED]")
            except:
                pass
            continue

        # ===== USER =====
        if isinstance(peer, types.PeerUser):
            user_id = peer.user_id

            if user_id in [assistant_id, bot_id]:
                continue

            # ADMIN CHECK
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
                await safe_edit(call, peer, True)
                continue

            # VIDEO / SCREEN
            video = hasattr(participant, "video") and participant.video
            screen = hasattr(participant, "presentation") and participant.presentation

            if (video or screen) and not is_admin:
                await safe_edit(call, peer, True)

# ==========================================
# ULTRA FAST MONITOR LOOP
# ==========================================
async def monitor_vc():
    while True:
        try:
            call = active_calls.get(str(config.GROUP_ID))
            if not call:
                await asyncio.sleep(2)
                continue

            result = await assistant(functions.phone.GetGroupParticipantsRequest(
                call=call,
                ids=[],
                sources=[],
                offset='',
                limit=100
            ))

            for participant in result.participants:
                peer = participant.peer

                if isinstance(peer, types.PeerUser):
                    user_id = peer.user_id

                    if user_id in [assistant_id, bot_id]:
                        continue

                    # ADMIN CHECK
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
                        continue

                    video = hasattr(participant, "video") and participant.video
                    screen = hasattr(participant, "presentation") and participant.presentation

                    if (video or screen) and not is_admin:
                        await safe_edit(call, peer, True)

        except Exception as e:
            print(f"[MONITOR ERROR] {e}")

        await asyncio.sleep(2)  # ⚡ ultra fast loop

# ==========================================
# WEB SERVER
# ==========================================
async def web_server():
    async def handle(request):
        return web.Response(text="VC Bot Running")

    app = web.Application()
    app.add_routes([web.get('/', handle)])

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, '0.0.0.0', config.PORT)
    await site.start()

# ==========================================
# MAIN
# ==========================================
async def main():
    global assistant_id, bot_id

    await bot.start(bot_token=config.BOT_TOKEN)
    bot_id = (await bot.get_me()).id

    await assistant.start()
    assistant_id = (await assistant.get_me()).id

    await web_server()

    print("🔥 ULTRA FAST VC CONTROL ACTIVE 🔥")

    asyncio.create_task(monitor_vc())

    await asyncio.gather(
        bot.run_until_disconnected(),
        assistant.run_until_disconnected()
    )

# ==========================================
# ENTRY
# ==========================================
if __name__ == "__main__":
    loop.run_until_complete(main())