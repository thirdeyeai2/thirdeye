import asyncio
import time
import os

from pyrogram import Client, enums
from pyrogram.types import ChatPermissions

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.phone import GetGroupCallRequest

# ================= CONFIG =================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION = os.getenv("SESSION")  # Telethon string session

# Groups to protect (replace with your group IDs)
PROTECTED_GROUPS = {
    -1003844395600: True,
}

# ================= CLIENTS =================

# Pyrogram bot client
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Telethon userbot client
userbot = TelegramClient(
    StringSession(SESSION),  # ✅ Correct usage
    API_ID,
    API_HASH
)

# ================= GLOBALS =================

FLAGGED_USERS = {}
LAST_ACTION = {}
COOLDOWN = 5  # seconds

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
            print(f"✅ Auto unmuted {user_id}")

        except Exception as e:
            print("Unmute error:", e)

# ================= VC SCANNER =================

async def vc_scanner():
    await userbot.start()
    print("👻 Userbot started (VC scanner active)")

    while True:
        for chat_id, enabled in PROTECTED_GROUPS.items():
            if not enabled:
                continue

            try:
                entity = await userbot.get_entity(chat_id)

                # Skip if no active call
                if not getattr(entity, "call", None):
                    continue

                call = await userbot(GetGroupCallRequest(call=entity.call))

                for p in call.participants:
                    if not hasattr(p, "peer"):
                        continue

                    now = time.time()

                    # 🔴 CHANNEL DETECT
                    if not hasattr(p.peer, "user_id"):
                        if now - LAST_ACTION.get(chat_id, 0) > COOLDOWN:
                            LAST_ACTION[chat_id] = now
                            print("⚠️ Channel detected in VC")
                        continue

                    user_id = p.peer.user_id

                    # 🔍 MEMBER CHECK
                    try:
                        member = await bot.get_chat_member(chat_id, user_id)
                        is_member = True
                    except:
                        is_member = False

                    # 🚫 NON-MEMBER
                    if not is_member:
                        FLAGGED_USERS.setdefault(chat_id, set()).add(user_id)

                        if now - LAST_ACTION.get(user_id, 0) > COOLDOWN:
                            LAST_ACTION[user_id] = now
                            try:
                                await bot.restrict_chat_member(chat_id, user_id, ChatPermissions())
                                print(f"🚫 Muted non-member {user_id}")
                            except Exception as e:
                                print("Mute error:", e)
                        continue

                    # 🔒 KEEP FLAGGED MUTED
                    if user_id in FLAGGED_USERS.get(chat_id, set()):
                        continue

                    # 📹 VIDEO ON DETECT
                    if getattr(p, "video", False):
                        if member.status in [
                            enums.ChatMemberStatus.ADMINISTRATOR,
                            enums.ChatMemberStatus.OWNER
                        ]:
                            continue

                        if now - LAST_ACTION.get(user_id, 0) > COOLDOWN:
                            LAST_ACTION[user_id] = now
                            try:
                                await bot.restrict_chat_member(chat_id, user_id, ChatPermissions())
                                print(f"📹 Muted video user {user_id}")
                            except Exception as e:
                                print("Video mute error:", e)

            except Exception as e:
                print("VC error:", e)

        await asyncio.sleep(1)  # ⚡ FAST LOOP

# ================= START =================

async def main():
    await bot.start()
    print("🤖 Bot started")

    # Run VC scanner in parallel
    await asyncio.gather(
        vc_scanner()
    )

if __name__ == "__main__":
    asyncio.run(main())