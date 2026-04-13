import config
import asyncio
import time
import logging
from aiohttp import web
from telethon import TelegramClient, events
from telethon.tl import types, functions
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# ==========================================
# LOGGING (PRO)
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ==========================================
# LOOP SETUP
# ==========================================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# ==========================================
# CLIENTS
# ==========================================
bot = TelegramClient(
    "bot_session",
    config.API_ID,
    config.API_HASH,
    loop=loop
)

assistant = TelegramClient(
    StringSession(config.SESSION_STRING),
    config.API_ID,
    config.API_HASH,
    loop=loop
)

# ==========================================
# GLOBALS
# ==========================================
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
    except Exception:
        try:
            if isinstance(peer, types.PeerUser):
                return await assistant.get_entity(int(peer.user_id))
            elif isinstance(peer, int):
                return await assistant.get_entity(peer)
        except Exception as e:
            logging.error(f"[ENTITY ERROR] {e}")
            return None

# ==========================================
# REFRESH VC CACHE
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
                offset="",
                limit=100
            ))
            last_refresh = time.time()
            logging.info("[CACHE] Refreshed VC participants")
        except Exception as e:
            logging.error(f"[CACHE ERROR] {e}")

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

        logging.info(f"[{'MUTED' if mute else 'UNMUTED'}] {peer}")

    except FloodWaitError as e:
        logging.warning(f"[FLOOD] Sleeping {e.seconds}s")
        await asyncio.sleep(e.seconds)
        return await safe_edit(call, peer, mute)

    except Exception as e:
        logging.error(f"[EDIT ERROR] {e}")

# ==========================================
# VC PARTICIPANT HANDLER
# ==========================================
@assistant.on(events.Raw(types.UpdateGroupCallParticipants))
async def vc_join_handler(event):
    try:
        call = event.call
        active_calls[str(config.GROUP_ID)] = call

        for participant in event.participants:
            if participant.left:
                continue

            peer_obj = participant.peer

            # ===== CHANNEL AUTO MUTE =====
            if isinstance(peer_obj, types.PeerChannel):
                logging.info(f"[CHANNEL] {peer_obj.channel_id} → Muting")

                try:
                    await assistant(functions.phone.EditGroupCallParticipantRequest(
                        call=call,
                        participant=peer_obj,
                        muted=True
                    ))
                    logging.info(f"[SUCCESS] Channel muted")

                except Exception as e:
                    logging.warning(f"[CHANNEL ERROR] {e}")
                    await refresh_cache(call)

                continue

            # ===== USER CHECK =====
            if isinstance(peer_obj, types.PeerUser):
                user_id = peer_obj.user_id

                if user_id in [assistant_id, bot_id]:
                    continue

                try:
                    await assistant(functions.channels.GetParticipantRequest(
                        channel=config.GROUP_ID,
                        participant=user_id
                    ))
                    logging.info(f"[MEMBER] {user_id}")

                except Exception:
                    logging.warning(f"[INTRUDER] {user_id} → Muting")
                    await safe_edit(call, peer_obj, True)

    except Exception as e:
        logging.error(f"[VC HANDLER ERROR] {e}")

# ==========================================
# AUTO UNMUTE ON JOIN
# ==========================================
@bot.on(events.ChatAction(chats=config.GROUP_ID))
async def group_join_handler(event):
    try:
        if not (event.user_joined or event.user_added):
            return

        user_id = event.user_id
        logging.info(f"[JOIN] {user_id}")

        full_chat = await assistant(functions.channels.GetFullChannelRequest(config.GROUP_ID))
        call = full_chat.full_chat.call

        if not call:
            return

        entity = await get_entity_safe(user_id)
        if not entity:
            return

        await safe_edit(call, entity, False)

    except Exception as e:
        logging.error(f"[UNMUTE ERROR] {e}")

# ==========================================
# WEB SERVER (KEEP ALIVE)
# ==========================================
async def web_server():
    async def handle(request):
        return web.Response(text="VC Bot Running ✅")

    app = web.Application()
    app.router.add_get("/", handle)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", config.PORT)
    await site.start()

    logging.info(f"[WEB] Running on port {config.PORT}")

# ==========================================
# MAIN START
# ==========================================
async def main():
    global assistant_id, bot_id

    await bot.start(bot_token=config.BOT_TOKEN)
    bot_id = (await bot.get_me()).id
    logging.info("Bot started")

    await assistant.start()
    assistant_id = (await assistant.get_me()).id
    logging.info("Assistant started")

    await web_server()

    logging.info("🛡️ VC AUTO MUTE SYSTEM ACTIVE 🛡️")

    await asyncio.gather(
        bot.run_until_disconnected(),
        assistant.run_until_disconnected()
    )

# ==========================================
# ENTRY
# ==========================================
if __name__ == "__main__":
    loop.run_until_complete(main())