import config
import asyncio
import time
from aiohttp import web
from telethon import TelegramClient, events
from telethon.tl import types, functions
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

==========================================

SETUP

==========================================

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

bot = TelegramClient('bot_session', config.API_ID, config.API_HASH, loop=loop)
assistant = TelegramClient(StringSession(config.SESSION_STRING), config.API_ID, config.API_HASH, loop=loop)

assistant_id = None
bot_id = None
last_refresh = 0

✅ FIX 1: define active_calls

active_calls = {}

==========================================

SAFE ENTITY FETCH

==========================================

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

==========================================

REFRESH CACHE

==========================================

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

==========================================

SAFE EDIT

==========================================

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

==========================================

VC HANDLER

==========================================

@assistant.on(events.Raw(types.UpdateGroupCallParticipants))
async def vc_join_handler(event):
call = event.call

# store call  
active_calls[config.GROUP_ID] = call  

for participant in event.participants:  
    if not participant.left:  
        peer_obj = participant.peer  

        # --- FEATURE 2: PERMANENT CHANNEL MUTE ---  
        if isinstance(peer_obj, types.PeerChannel):  
            print(f"[FEATURE 2] Channel detected (ID: {peer_obj.channel_id}) → muting")  

            try:  
                await assistant(functions.phone.EditGroupCallParticipantRequest(  
                    call=call,  
                    participant=peer_obj,  
                    muted=True  
                ))  
                print(f"[SUCCESS] Channel {peer_obj.channel_id} muted")  

            except ValueError:  
                print(f"[CACHE REFRESH] Unknown channel {peer_obj.channel_id}")  

                try:  
                    await assistant(functions.phone.GetGroupParticipantsRequest(  
                        call=call,  
                        ids=[],  
                        sources=[],  
                        offset='',  
                        limit=100  
                    ))  

                    await assistant(functions.phone.EditGroupCallParticipantRequest(  
                        call=call,  
                        participant=peer_obj,  
                        muted=True  
                    ))  

                    print(f"[SUCCESS] Channel {peer_obj.channel_id} muted after refresh")  

                except Exception as e:  
                    print(f"[ERROR] Channel mute failed: {e}")  

            except Exception as e:  
                print(f"[ERROR] Failed to mute channel: {e}")  

            continue  

        # ===== USER =====  
        if isinstance(peer_obj, types.PeerUser):  
            user_id = peer_obj.user_id  

            if user_id in [assistant_id, bot_id]:  
                continue  

            try:  
                await assistant(functions.channels.GetParticipantRequest(  
                    channel=config.GROUP_ID,  
                    participant=user_id  
                ))  
                print(f"[OK] {user_id} is member")  

            except:  
                print(f"[INTRUDER] {user_id} → Muting")  
                await safe_edit(call, peer_obj, True)

==========================================

AUTO UNMUTE

==========================================

@bot.on(events.ChatAction(chats=config.GROUP_ID))
async def group_join_handler(event):
if event.user_joined or event.user_added:
user_id = event.user_id

print(f"[JOIN] {user_id}")  

    try:  
        full_chat = await assistant(functions.channels.GetFullChannelRequest(config.GROUP_ID))  
        call = full_chat.full_chat.call  

        if not call:  
            return  

        entity = await get_entity_safe(user_id)  
        if not entity:  
            return  

        print(f"[UNMUTE] {user_id}")  
        await safe_edit(call, entity, False)  

    except Exception as e:  
        print(f"[UNMUTE ERROR] {e}")

==========================================

WEB SERVER (Heroku keep alive)

==========================================

async def web_server():
async def handle(request):
return web.Response(text="VC Bot Running ✅")

app = web.Application()  
app.add_routes([web.get('/', handle)])  

runner = web.AppRunner(app)  
await runner.setup()  

site = web.TCPSite(runner, '0.0.0.0', config.PORT)  
await site.start()

==========================================

START

==========================================

async def main():
global assistant_id, bot_id

await bot.start(bot_token=config.BOT_TOKEN)  
bot_id = (await bot.get_me()).id  
print("Bot started")  

await assistant.start()  
assistant_id = (await assistant.get_me()).id  
print("Assistant started")  

await web_server()  

print("🛡️ VC AUTO MUTE SYSTEM ACTIVE 🛡️")  

await asyncio.gather(  
    bot.run_until_disconnected(),  
    assistant.run_until_disconnected()  
)

if name == "main":
loop.run_until_complete(main())