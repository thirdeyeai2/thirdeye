from pyrogram import Client, filters, enums
from pyrogram.types import ChatPermissions
from dotenv import load_dotenv
import os

# ================= LOAD ENV =================
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise ValueError("❌ Missing API_ID / API_HASH / BOT_TOKEN")

API_ID = int(API_ID)

# ================= APP =================
app = Client(
    "ThirdEye2",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

PROTECTED_GROUPS = {}  # {chat_id: True/False}

# ================= COMMAND =================
@app.on_message(filters.command("thirdeye"))
async def toggle_protection(client, message):
    chat_id = message.chat.id
    PROTECTED_GROUPS[chat_id] = not PROTECTED_GROUPS.get(chat_id, False)

    status = "🟢 ENABLED" if PROTECTED_GROUPS[chat_id] else "🔴 DISABLED"

    await message.reply(
        f"**Third Eye 2.0 {status}**\n"
        "👁️ Auto-mute: non-members & VC users"
    )

# ================= VC PROTECTION =================
@app.on_voice_chat_members_updated()
async def vc_protection(client, event):
    chat_id = event.chat.id

    if not PROTECTED_GROUPS.get(chat_id):
        return

    # Pyrogram gives a list of participants
    for member in event.participants:
        user = member.user
        user_id = user.id

        username = user.username or user.first_name or "User"

        try:
            chat_member = await client.get_chat_member(chat_id, user_id)

            if not chat_member:
                continue

            status = chat_member.status

            # 🚫 Non-members
            if status == enums.ChatMemberStatus.LEFT:
                await client.restrict_chat_member(
                    chat_id,
                    user_id,
                    ChatPermissions()  # no permissions
                )

                await client.send_message(
                    chat_id,
                    f"🚫 {username} muted (non-member)"
                )

            # 📹 Video ON detection
            if member.is_self is False and member.video:
                await client.restrict_chat_member(
                    chat_id,
                    user_id,
                    ChatPermissions()
                )

                await client.send_message(
                    chat_id,
                    f"📹 {username} muted (video on)"
                )

        except Exception as e:
            print(f"Error: {e}")

# ================= START =================
print("👁️ Third Eye 2.0 Live!")
app.run()