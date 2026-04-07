import os
import asyncio
from dotenv import load_dotenv

# BOT
from pyrogram import Client, filters, enums
from pyrogram.types import ChatPermissions

# USERBOT
from telethon import TelegramClient
from telethon.tl.functions.phone import GetGroupCallRequest

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ================= INIT =================
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = TelegramClient("userbot", API_ID, API_HASH)

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

# ================= AUTO MESSAGE PROTECTION =================
@bot.on_message(filters.group & ~filters.service)
async def auto_protect(_, message):
    chat_id = message.chat.id

    if not PROTECTED_GROUPS.get(chat_id):
        return

    user = message.from_user
    if not user:
        return

    user_id = user.id
    username = user.username or user.first_name or "User"

    try:
        member = await bot.get_chat_member(chat_id, user_id)

        # Skip admins
        if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return

        # 🚫 Non-members
        if member.status == enums.ChatMemberStatus.LEFT:
            await bot.restrict_chat_member(chat_id, user_id, ChatPermissions())
            await message.reply(f"🚫 {username} muted (non-member)")

        # 🚫 Channel accounts
        if message.sender_chat:
            await bot.delete_messages(chat_id, message.id)
            await message.reply("🚫 Channel account muted")

    except Exception as e:
        print("Message protection error:", e)

# ================= VC SCANNER (ULTRA FAST) =================
async def vc_scanner():
    while True:
        for chat_id in PROTECTED_GROUPS:
            if not PROTECTED_GROUPS.get(chat_id):
                continue

            try:
                call = await userbot(GetGroupCallRequest(peer=chat_id, limit=100))

                for p in call.participants:
                    if not hasattr(p, "peer") or not hasattr(p.peer, "user_id"):
                        continue

                    user_id = p.peer.user_id

                    # 🎥 VIDEO DETECTION
                    if getattr(p, "video", False):

                        try:
                            member = await bot.get_chat_member(chat_id, user_id)

                            # Skip admins
                            if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                                continue

                            await bot.restrict_chat_member(
                                chat_id,
                                user_id,
                                ChatPermissions()
                            )

                            await bot.send_message(
                                chat_id,
                                f"📹 User muted (video ON)"
                            )

                        except Exception as e:
                            print("Mute error:", e)

            except Exception as e:
                print("VC error:", e)

        await asyncio.sleep(2)  # ⚡ FAST LOOP

# ================= MAIN =================
async def main():
    await bot.start()
    await userbot.start()

    print("👁️ Third Eye 2.0 GOD MODE RUNNING")

    await asyncio.gather(
        bot.idle(),
        vc_scanner()
    )

asyncio.run(main())