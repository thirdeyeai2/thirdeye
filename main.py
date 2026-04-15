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
video_state = {}

# ==========================================
# SAFE ENTITY FETCH
# ==========================================
async def get_entity_safe(peer):
    try:
        return await assistant.get_input_entity(peer)
    except:
        try:
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

    if time.time() - last_refresh > 2:
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

    # ⚡ reduced cooldown (allows re-mute)
    if mute and user_id:
        now = time.time()
        if user_id in muted_users:
            if now - muted_users[user_id] < 1:
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

        print(f"[MUTED] {user_id if user_id else peer}")

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

    await refresh_cache(call)

    for participant in event.participants:
        if participant.left:
            continue

        peer = participant.peer

        # ===== CHANNEL =====
        if isinstance(peer, types.PeerChannel):
            try:
                entity = await assistant.get_entity(peer.channel_id)

                await assistant(functions.phone.EditGroupCallParticipantRequest(
                    call=call,
                    participant=entity,
                    muted=True
                ))

                print(f"[CHANNEL MUTED] {peer.channel_id}")
            except Exception as e:
                print(f"[CHANNEL ERROR] {e}")
            continue

        # ===== USER =====
        if isinstance(peer, types.PeerUser):
            user_id = peer.user_id

            if user_id in [assistant_id, bot_id]:
                continue

            # ADMIN / MEMBER CHECK
            is_admin = False
            is_member = True

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
                is_member = False

            # 🚨 INTRUDER
            if not is_member:
                print(f"[INTRUDER] {user_id}")
                await safe_edit(call, peer, True)
                continue

            # 🎥 VIDEO / SCREEN
            video = getattr(participant, "video", None) is not None
            screen = getattr(participant, "presentation", None) is not None

            key = str(user_id)

            if (video or screen) and not is_admin:
                print(f"[VIDEO/SCREEN ON] {user_id}")
                video_state[key] = "on"
                await safe_edit(call, peer, True)
            else:
                video_state[key] = "off"

# ==========================================
# MONITOR LOOP (ULTRA FAST + FINAL FIX)
# ==========================================
async def monitor_vc():
    while True:
        try:
            call = active_calls.get(str(config.GROUP_ID))
            if not call:
                await asyncio.sleep(1)
                continue

            await refresh_cache(call)

            result = await assistant(functions.phone.GetGroupParticipantsRequest(
                call=call,
                ids=[],
                sources=[],
                offset='',
                limit=100
            ))

            for participant in result.participants:
                peer = participant.peer

                # ===== CHANNEL =====
                if isinstance(peer, types.PeerChannel):
                    try:
                        entity = await assistant.get_entity(peer.channel_id)

                        await assistant(functions.phone.EditGroupCallParticipantRequest(
                            call=call,
                            participant=entity,
                            muted=True
                        ))

                        print(f"[FORCE CHANNEL MUTE] {peer.channel_id}")
                    except:
                        pass
                    continue

                # ===== USER =====
                if isinstance(peer, types.PeerUser):
                    user_id = peer.user_id

                    if user_id in [assistant_id, bot_id]:
                        continue

                    is_admin = False
                    is_member = True

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
                        is_member = False

                    # 🚨 INTRUDER LOOP FIX
                    if not is_member:
                        print(f"[FORCE INTRUDER MUTE] {user_id}")
                        await safe_edit(call, peer, True)
                        continue

                    # 🎥 VIDEO / SCREEN LOOP
                    video = getattr(participant, "video", None) is not None
                    screen = getattr(participant, "presentation", None) is not None

                    key = str(user_id)

                    if (video or screen) and not is_admin:
                        print(f"[FORCE VIDEO MUTE] {user_id}")
                        video_state[key] = "on"
                        await safe_edit(call, peer, True)
                    else:
                        video_state[key] = "off"

        except Exception as e:
            print(f"[MONITOR ERROR] {e}")

        await asyncio.sleep(1)

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

    # 🔥 IMPORTANT
    await assistant.get_dialogs()

    await web_server()

    print("🔥 ABSOLUTE VC CONTROL ACTIVE 🔥")

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