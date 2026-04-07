from pyrogram import Client, filters, enums
from pyrogram.types import ChatMember
import asyncio
import os

# ================= ENV =================
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise ValueError("Missing API_ID / API_HASH / BOT_TOKEN")

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
        "👁️ Auto-mute: non-members, channels, video-call users"
    )

# ================= VC PROTECTION =================
@app.on_voice_chat_members_updated()
async def vc_protection(client, event):
    chat_id = event.chat.id

    if not PROTECTED_GROUPS.get(chat_id):
        return

    actions = [
        event.voice_chat_members_added,
        event.voice_chat_members_removed
    ]

    for action in actions:
        if not action:
            continue

        for member in action:
            user_id = member.user.id

            # ✅ SAFE USERNAME HANDLING
            username = member.user.username or member.user.first_name or "User"

            try:
                chat_member = await client.get_chat_member(chat_id, user_id)
                status = chat_member.status

                # 🚫 Non-members / channels
                if status == enums.ChatMemberStatus.LEFT or "channel" in str(member.user):
                    await client.edit_chat_member_permissions(
                        chat_id,
                        user_id,
                        can_send_messages=False,
                        can_send_media_messages=False
                    )

                    await client.send_message(
                        chat_id,
                        f"🚫 {username} muted (non-member/channel)"
                    )

                # 📹 Video chat detection
                elif event.video_chat_participants_invited:
                    await client.edit_chat_member_permissions(
                        chat_id,
                        user_id,
                        can_send_messages=False
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