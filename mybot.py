from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN
import json
from io import BytesIO
import logging

# ===== LOGGING =====
logging.basicConfig(level=logging.INFO)

# ===== STATUS =====
def get_status():
    with open("status.json") as f:
        return json.load(f).get("vc", False)

def set_status(v):
    with open("status.json", "w") as f:
        json.dump({"vc": v}, f)

# ===== ADMIN CHECK =====
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    member = await context.bot.get_chat_member(chat_id, user_id)
    return member.status in ["administrator", "creator"]

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
            InlineKeyboardButton("📄 SEND FILE", callback_data="send_file")  # Example file button
        ]
    ]

    return text, InlineKeyboardMarkup(buttons)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, btn = panel()
    await update.message.reply_text(text, reply_markup=btn, parse_mode="HTML")

# ===== BUTTON HANDLER =====
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query

    try:
        # Respond immediately to avoid "Query too old" errors
        await q.answer("Processing...", show_alert=False)

        # Admin check
        if not await is_admin(update, context):
            await q.answer("Admins only ❌", show_alert=True)
            return

        # Handle VC status buttons
        if q.data == "on":
            set_status(True)
        elif q.data == "off":
            set_status(False)
        elif q.data == "refresh":
            pass  # just refresh panel
        elif q.data == "send_file":
            # ✅ Send file safely using BytesIO
            file_bytes = b"Hello! This is an example file from your bot."
            file_like = BytesIO(file_bytes)
            file_like.name = "example.txt"  # Telegram requires a name for BytesIO
            await context.bot.send_document(chat_id=q.message.chat.id, document=file_like, filename="example.txt")
            await q.answer("File sent ✅", show_alert=True)
            return  # stop further panel refresh

        # Update panel
        text, btn = panel()
        await q.edit_message_text(text, reply_markup=btn, parse_mode="HTML")

    except Exception as e:
        logging.error(f"Error in button handler: {e}")
        try:
            await q.answer("Something went wrong ❌", show_alert=True)
        except:
            pass

# ===== RUN BOT =====
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

print("🤖 UI BOT RUNNING")
app.run_polling()