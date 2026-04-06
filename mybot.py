# mybot.py
import json
import asyncio
import logging
from io import BytesIO
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
from pyrogram import Client
from config import BOT_TOKEN, API_ID, API_HASH, GROUPS

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
        [InlineKeyboardButton("✅ ENABLE", callback_data="on"),
         InlineKeyboardButton("❌ DISABLE", callback_data="off")],
        [InlineKeyboardButton("🔄 REFRESH", callback_data="refresh"),
         InlineKeyboardButton("📄 SEND FILE", callback_data="send_file")],
        [InlineKeyboardButton("♻️ RESTART VC", callback_data="restart_vc")]
    ]

    return text, InlineKeyboardMarkup(buttons)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, btn = panel()
    await update.message.reply_text(text, reply_markup=btn, parse_mode="HTML")

# ===== RESTART VC ENGINE =====
app_pyro = Client("vc_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def restart_vc_engine(q=None):
    global app_pyro
    try:
        await app_pyro.stop()
    except:
        pass

    app_pyro = Client("vc_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
    asyncio.create_task(app_pyro.start())

    # Auto-refresh panel if called from a button
    if q:
        text, btn = panel()
        await q.edit_message_text(text, reply_markup=btn, parse_mode="HTML")

# ===== BUTTON HANDLER =====
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try:
        await q.answer("Processing...", show_alert=False)

        if not await is_admin(update, context):
            await q.answer("Admins only ❌", show_alert=True)
            return

        if q.data == "on":
            set_status(True)
        elif q.data == "off":
            set_status(False)
        elif q.data == "send_file":
            file_bytes = b"Hello! This is an example file from your bot."
            file_like = BytesIO(file_bytes)
            file_like.name = "example.txt"
            await context.bot.send_document(chat_id=q.message.chat.id, document=file_like)
            await q.answer("File sent ✅", show_alert=True)
            return
        elif q.data == "restart_vc":
            await restart_vc_engine(q)
            await q.answer("VC Engine Restarted ✅", show_alert=True)
            return

        # Refresh panel
        text, btn = panel()
        await q.edit_message_text(text, reply_markup=btn, parse_mode="HTML")

    except Exception as e:
        logging.error(f"Button handler error: {e}")
        try:
            await q.answer("Something went wrong ❌", show_alert=True)
        except: pass

# ===== BAD WORD FILTER =====
BAD_WORDS = ["porn", "sex", "xxx", "nude"]

@app_pyro.on_message()
async def filter_msg(client, msg):
    if not msg.text:
        return
    text = msg.text.lower()
    for w in BAD_WORDS:
        if w in text:
            try:
                await client.kick_chat_member(msg.chat.id, msg.from_user.id)
            except: pass

# ===== VC CONTROL =====
LAST = 0
COOLDOWN = 2
from collections import defaultdict
MIC_TRACK = defaultdict(list)

def is_enabled():
    return get_status()

@app_pyro.on_raw_update()
async def vc(client, update, users, chats):
    global LAST
    if not is_enabled():
        return
    try:
        if hasattr(update, "participants"):
            for gid in GROUPS:
                actions = []
                for p in update.participants:
                    if not hasattr(p.peer, "user_id"):
                        continue
                    uid = p.peer.user_id
                    try:
                        m = await client.get_chat_member(gid, uid)
                        role = m.status
                    except:
                        role = "none"

                    if role in ["administrator", "creator"]:
                        continue

                    mute = False
                    if role != "member":
                        mute = True
                    if hasattr(p.peer, "channel_id"):
                        mute = True
                    if hasattr(p, "video") and p.video:
                        mute = True

                    # Mic spam check
                    now = asyncio.get_event_loop().time()
                    MIC_TRACK[uid].append(now)
                    MIC_TRACK[uid] = [t for t in MIC_TRACK[uid] if now - t < 5]

                    if len(MIC_TRACK[uid]) > 5:
                        mute = True

                    actions.append((p.peer, mute))

                if actions and asyncio.get_event_loop().time() - LAST > COOLDOWN:
                    LAST = asyncio.get_event_loop().time()
                    await client.invoke(
                        JoinGroupCall(
                            call=update.call,
                            join_as=await client.resolve_peer("me"),
                            params=b'{"muted": true}'
                        )
                    )
                    for peer, mute in actions:
                        await client.invoke(
                            EditGroupCallParticipant(
                                call=update.call,
                                participant=peer,
                                muted=mute
                            )
                        )
                    await asyncio.sleep(0.3)
                    await client.invoke(LeaveGroupCall(call=update.call))

    except Exception as e:
        logging.error(e)

# ===== RUN TELEGRAM BOT =====
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

print("🤖 UI BOT RUNNING")
asyncio.create_task(app_pyro.start())
app.run_polling()