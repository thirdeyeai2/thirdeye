import asyncio
import os
import time

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.phone import GetGroupCallRequest, ToggleGroupCallParticipant
from telethon.tl.types import InputPeerUser

from pyrogram import Client, enums
from pyrogram.types import ChatPermissions

# ================= CONFIG =================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION = os.getenv("SESSION")  # Userbot string session
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Optional, for auto-unmute

# Replace with your target groups
PROTECTED_GROUPS = {
    -1001747095956: True,
}

COOLDOWN = 5  # seconds

# ================= CLIENTS =================

userbot = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================= GLOBALS =================

FLAGGED_USERS = {}
LAST_ACTION = {}

# ================= AUTO UNMUTE =================

@bot.on_chat_member_updated()
async def auto_unmute(_, update):
    chat_id = update.chat.id
    user = update.new_chat_member.user
    if not user:
        return

    user_id = user.id
    if user_id in FLAGGED_USERS.get(chat_id, set()):
        try:
            await bot.restrict_chat_member(
                chat_id,
                user_id,
                ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )
            FLAGGED_USERS[chat_id].remove(user_id)
            print(f"✅ Auto-unmuted {user_id}")
        except Exception as e:
            print("Unmute error:", e)

# ================= VC SCANNER =================

async def vc_scanner():
    await userbot.start()
    print("👻 Userbot started (Elite VC scanner active)")

    while True:
        for chat_id, enabled in PROTECTED_GROUPS.items():
            if not enabled:
                continue
            try:
                entity = await userbot.get_entity(chat_id)
                if not getattr(entity, "call", None):
                    continue

                call = await userbot(GetGroupCallRequest(call=entity.call))
                for p in call.participants:
                    if not hasattr(p, "peer"):
                        continue

                    now = time.time()

                    # Channel detection
                    if not hasattr(p.peer, "user_id"):
                        if now - LAST_ACTION.get(chat_id, 0) > COOLDOWN:
                            LAST_ACTION[chat_id] = now
                            print("⚠️ Channel detected in VC")
                        continue

                    user_id = p.peer.user_id

                    # Non-member handling
                    try:
                        member = await bot.get_chat_member(chat_id, user_id)
                        is_member = True
                    except:
                        is_member = False

                    if not is_member:
                        FLAGGED_USERS.setdefault(chat_id, set()).add(user_id)
                        if now - LAST_ACTION.get(user_id, 0) > COOLDOWN:
                            LAST_ACTION[user_id] = now
                            try:
                                await userbot(ToggleGroupCallParticipant(
                                    call=entity.call,
                                    participant=InputPeerUser(user_id, 0),
                                    muted=True
                                ))
                                print(f"🚫 Muted non-member {user_id} in VC")
                            except Exception as e:
                                print("Mute non-member error:", e)
                        continue

                    # Keep flagged users muted
                    if user_id in FLAGGED_USERS.get(chat_id, set()):
                        continue

                    # Video detection mute
                    if getattr(p, "video", False):
                        if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                            continue
                        if now - LAST_ACTION.get(user_id, 0) > COOLDOWN:
                            LAST_ACTION[user_id] = now
                            try:
                                await userbot(ToggleGroupCallParticipant(
                                    call=entity.call,
                                    participant=InputPeerUser(user_id, 0),
                                    muted=True
                                ))
                                print(f"📹 Muted video user {user_id}")
                            except Exception as e:
                                print("Video mute error:", e)

            except Exception as e:
                print("VC scanner error:", e)

        await asyncio.sleep(1)

# ================= START =================

async def main():
    await bot.start()
    print("🤖 Bot started")
    await vc_scanner()

if __name__ == "__main__":
    asyncio.run(main())