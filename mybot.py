from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN
import json

# ===== STATUS =====
def get_status():
    with open("status.json") as f:
        return json.load(f)["vc"]

def set_status(v):
    with open("status.json", "w") as f:
        json.dump({"vc": v}, f)

# ===== ADMIN CHECK =====
async def is_admin(update, context):
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
            InlineKeyboardButton("🔄 REFRESH", callback_data="refresh")
        ]
    ]

    return text, InlineKeyboardMarkup(buttons)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, btn = panel()
    await update.message.reply_text(text, reply_markup=btn, parse_mode="HTML")

# ===== BUTTON =====
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query

    if not await is_admin(update, context):
        await q.answer("Admins only ❌", show_alert=True)
        return

    if q.data == "on":
        set_status(True)
    elif q.data == "off":
        set_status(False)

    text, btn = panel()
    await q.edit_message_text(text, reply_markup=btn, parse_mode="HTML")

# ===== RUN =====
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

print("🤖 UI BOT RUNNING")
app.run_polling()