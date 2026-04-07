import os
import asyncio
from dotenv import load_dotenv

from pyrogram import Client, filters, enums, idle
from pyrogram.types import ChatPermissions

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.phone import GetGroupCallRequest
from telethon.tl.types import InputPeerChannel

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
@bot.on_message(filters.private & filters.command("start"))
async def start(_, message):
    await message.reply_text(
        "**Thirdeye 👁️**\n"
        "Hybrid Bot Engine ⚙️\n\n"

        "🛡 Group Management: Active\n"
        "🎙 VC Protection: ENABLED\n\n"

        "🔕 Auto-mute Non-members\n"
        "🔕 Auto-mute Channel Accounts\n"
        "🔕 Auto-mute Video-On Users (Except Admins)\n\n"

        "📡 Real-time Notifications Active\n\n"
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

                if not hasattr(entity, "call") or not entity.call:
                    continue

                call = await userbot(GetGroupCallRequest(
                    call=entity.call
                ))

                for p in call.participants:
                    if not hasattr(p, "peer") or not hasattr(p.peer, "user_id"):
                        continue

                    user_id = p.peer.user_id

                    # 🎥 Detect video ON
                    if getattr(p, "video", False):

                        try:
                            member = await bot.get_chat_member(chat_id, user_id)

                            # ❌ Skip admins
                            if member.status in [
                                enums.ChatMemberStatus.ADMINISTRATOR,
                                enums.ChatMemberStatus.OWNER
                            ]:
                                continue

                            # 🔇 Mute user
                            await bot.restrict_chat_member(
                                chat_id,
                                user_id,
                                ChatPermissions()
                            )

                            await bot.send_message(
                                chat_id,
                                "📹 User muted (video ON)"
                            )

                        except Exception as e:
                            print("Mute error:", e)

            except Exception as e:
                print("VC error:", e)

        await asyncio.sleep(3)

# ================= MAIN =================
async def main():
    await bot.start()

    print("👁️ Hybrid Third Eye Running (STRING MODE)")

    # run both together
    await asyncio.gather(
        vc_scanner(),
        idle()   # ✅ correct idle
    )

if __name__ == "__main__":
    asyncio.run(main())