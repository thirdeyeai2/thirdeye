import os
import asyncio
from dotenv import load_dotenv

from pyrogram import Client, filters, enums, idle
from pyrogram.types import ChatPermissions

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.phone import GetGroupCallRequest

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
STRING_SESSION = os.getenv("STRING_SESSION")

# ================= CLIENTS =================
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

userbot = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH
)

PROTECTED_GROUPS = {}

# ================= START PANEL =================
@bot.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text(
        "**Thirdeye 👁️**\n"
        "Hybrid Bot Engine ⚙️\n\n"

        "🛡 Group Management: Active\n"
        "🎙 VC Protection: ENABLED\n\n"

        "🔕 Auto-mute Non-members\n"
        "🔕 Auto-mute Channel Accounts\n"
        "🔕 Auto-mute Video-On Users (Except Admins)\n\n"

        "📡 Real-time Protection Active\n\n"
        "✉️ Contact: @vettipeace"
    )

# ================= TOGGLE =================
@bot.on_message(filters.group & filters.command("thirdeye"))
async def toggle(_, message):
    chat_id = message.chat.id

    member = await bot.get_chat_member(chat_id, message.from_user.id)
    if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
        return await message.reply("❌ Admin only")

    PROTECTED_GROUPS[chat_id] = not PROTECTED_GROUPS.get(chat_id, False)

    status = "🟢 ENABLED" if PROTECTED_GROUPS[chat_id] else "🔴 DISABLED"
    await message.reply(f"👁️ Protection {status}")

# ================= VC SCANNER =================
async def vc_scanner():
    await userbot.start()

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

                    # Skip invalid
                    if not hasattr(p, "peer"):
                        continue

                    # 🚫 CHANNEL / INVALID
                    if not hasattr(p.peer, "user_id"):
                        continue

                    user_id = p.peer.user_id

                    # 🔍 Check membership
                    try:
                        member = await bot.get_chat_member(chat_id, user_id)
                        is_member = True
                    except:
                        is_member = False

                    # 🚫 NON-MEMBER AUTO MUTE
                    if not is_member:
                        try:
                            await bot.restrict_chat_member(
                                chat_id,
                                user_id,
                                ChatPermissions()
                            )
                        except:
                            pass
                        continue

                    # 📹 VIDEO DETECT
                    if getattr(p, "video", False):

                        try:
                            member = await bot.get_chat_member(chat_id, user_id)

                            # Skip admins
                            if member.status in [
                                enums.ChatMemberStatus.ADMINISTRATOR,
                                enums.ChatMemberStatus.OWNER
                            ]:
                                continue

                            await bot.restrict_chat_member(
                                chat_id,
                                user_id,
                                ChatPermissions()
                            )

                        except:
                            pass

            except Exception as e:
                print("VC error:", e)

        await asyncio.sleep(2)  # ⚡ FAST SCAN

# ================= MAIN =================
async def main():
    await bot.start()

    # Fix webhook issues
    try:
        await bot.delete_webhook()
    except:
        pass

    print("👁️ Hybrid Third Eye PRO Running")

    await asyncio.gather(
        vc_scanner(),
        idle()
    )

if __name__ == "__main__":
    asyncio.run(main())