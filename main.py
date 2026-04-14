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
assistant = TelegramClient(StringSession(config.SESSION_STRING), config.API_ID, config.API_HASH, loop=loop)

assistant_id = None
bot_id = None
last_refresh = 0

active_calls = {}
recent_joins = set()

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

    # store call
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

            # AUTO UNMUTE LOGIC
            if user_id in recent_joins:
                print(f"[AUTO UNMUTE] {user_id}")
                await safe_edit(call, peer_obj, False)
                recent_joins.remove(user_id)
                continue

            # NORMAL MEMBER CHECK
            try:
                await assistant(functions.channels.GetParticipantRequest(
                    channel=config.GROUP_ID,
                    participant=user_id
                ))
                print(f"[OK] {user_id} is member")

            except:
                print(f"[INTRUDER] {user_id} → Muting")
                await safe_edit(call, peer_obj, True)

# ==========================================
# GROUP JOIN TRACK
# ==========================================
@bot.on(events.ChatAction(chats=config.GROUP_ID))
async def group_join_handler(event):
    if event.user_joined or event.user_added:
        user_id = event.user_id

        print(f"[JOIN DETECTED] {user_id}")

        # store for auto unmute
        recent_joins.add(user_id)

# ==========================================
# CLEAN OLD JOINS (OPTIONAL SAFETY)
# ==========================================
async def clear_old_joins():
    while True:
        await asyncio.sleep(300)
        recent_joins.clear()
        print("[CLEANUP] recent joins cleared")

# ==========================================
# WEB SERVER (KEEP ALIVE)
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

    # start cleanup task
    asyncio.create_task(clear_old_joins())

    print("🛡️ VC AUTO MUTE SYSTEM ACTIVE 🛡️")

    await asyncio.gather(
        bot.run_until_disconnected(),
        assistant.run_until_disconnected()
    )

# ==========================================
# ENTRY
# ==========================================
if __name__ == "__main__":
    loop.run_until_complete(main())