from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN
import json
from io import BytesIO
import logging

# ===== LOGGING =====
logging.basicConfig(level=logging.INFO)

# ===== STATUS =====
def get_status():
    try:
        with open("status.json") as f:
            return json.load(f).get("vc", False)
    except:
        return False

def set_status(v: bool):
    with open("status.json", "w") as f:
        json.dump({"vc": v}, f)

# ===== ADMIN CHECK =====
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception as e:
        logging.error(f"Admin check failed: {e}")
        return False

# ===== PANEL =====
def panel():
    status = "🟢 ENABLED" if get_status() else "🔴 DISABLED"
    text = f"""
👁️ <b>Third Eye 2.0</b>

⚙️ VC Protection: {status}

🚫 Auto-mute Non-members
🚫 Auto-mute Channel Accounts
🚫 Auto-mute Video Users

🧠 Anti Spam Active
📡 Monitoring Live
"""

    buttons = [
        [
            InlineKeyboardButton("✅ ENABLE", callback_data="on"),
            InlineKeyboardButton("❌ DISABLE", callback_data="off")
        ],
        [
            InlineKeyboardButton("🔄 REFRESH", callback_data="refresh"),
            InlineKeyboardButton("📄 SEND FILE", callback_data="send_file")
        ]
    ]

    return text, InlineKeyboardMarkup(buttons)

# ===== START COMMAND =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text, btn = panel()
        await update.message.reply_text(text, reply_markup=btn, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Start command failed: {e}")

# ===== BUTTON HANDLER =====
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query

    try:
        await q.answer(show_alert=False)

        if not await is_admin(update, context):
            await q.answer("Admins only ❌", show_alert=True)
            return

        if q.data == "on":
            set_status(True)
            await q.answer("VC Enabled ✅", show_alert=True)
        elif q.data == "off":
            set_status(False)
            await q.answer("VC Disabled ❌", show_alert=True)
        elif q.data == "refresh":
            await q.answer("Panel refreshed 🔄", show_alert=True)
        elif q.data == "send_file":
            file_bytes = b"Hello! This is your file from the bot."
            file_like = BytesIO(file_bytes)
            file_like.name = "example.txt"
            try:
                await context.bot.send_document(chat_id=q.message.chat.id, document=file_like, filename="example.txt")
                await q.answer("File sent ✅", show_alert=True)
            except Exception as e:
                logging.error(f"Send file failed: {e}")
                await q.answer("Failed to send file ❌", show_alert=True)
            return

        text, btn = panel()
        await q.edit_message_text(text, reply_markup=btn, parse_mode="HTML")

    except Exception as e:
        logging.error(f"Button handler error: {e}")
        try:
            await q.answer("Something went wrong ❌", show_alert=True)
        except:
            pass

# ===== RUN BOT =====
async def main():
    # Delete any existing webhook to prevent 409 Conflict
    try:
        bot = Bot(BOT_TOKEN)
        await bot.delete_webhook()
        logging.info("Webhook deleted ✅")
    except Exception as e:
        logging.error(f"Failed to delete webhook: {e}")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    print("🤖 UI BOT RUNNING")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())