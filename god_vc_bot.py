import json, asyncio, time
from collections import defaultdict
from io import BytesIO
import logging

from pyrogram import Client
from pyrogram.raw.functions.phone import JoinGroupCall, LeaveGroupCall, EditGroupCallParticipant
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

# ================= CONFIG =================
BOT_TOKEN = "8040350855:AAEaKZj6pRY5_8Weajb0jo6MWyWNEtOFQdk"
API_ID = 35632117
API_HASH = "5c619323bc6b20b0c120886ae1316e27"
GROUPS = [-1001747095956]  # replace with your group IDs

BAD_WORDS = ["porn", "sex", "xxx", "nude"]
COOLDOWN = 2

# ================= STATUS =================
STATUS_FILE = "status.json"

def get_status():
    try:
        with open(STATUS_FILE) as f:
            return json.load(f).get("vc", False)
    except:
        return False

def set_status(v):
    with open(STATUS_FILE, "w") as f:
        json.dump({"vc": v}, f)

# ================= TELEGRAM PANEL =================
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
         InlineKeyboardButton("📄 SEND FILE", callback_data="send_file")]
    ]
    return text, InlineKeyboardMarkup(buttons)

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    member = await context.bot.get_chat_member(chat_id, user_id)
    return member.status in ["administrator", "creator"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, btn = panel()
    await update.message.reply_text(text, reply_markup=btn, parse_mode="HTML")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Processing...", show_alert=False)
    if not await is_admin(update, context):
        await q.answer("Admins only ❌", show_alert=True)
        return
    if q.data == "on":
        set_status(True)
    elif q.data == "off":
        set_status(False)
    elif q.data == "send_file":
        file_like = BytesIO(b"Hello! This is an example file from your bot.")
        file_like.name = "example.txt"
        await context.bot.send_document(chat_id=q.message.chat.id, document=file_like, filename="example.txt")
        await q.answer("File sent ✅", show_alert=True)
        return
    text, btn = panel()
    await q.edit_message_text(text, reply_markup=btn, parse_mode="HTML")

# ================= PYROGRAM VC ENGINE =================
vc_app = Client("vc_god", api_id=API_ID, api_hash=API_HASH)
LAST = 0
MIC_TRACK = defaultdict(list)

@vc_app.on_message()
async def filter_msg(client, msg):
    if not msg.text: return
    text = msg.text.lower()
    for w in BAD_WORDS:
        if w in text:
            try: await client.kick_chat_member(msg.chat.id, msg.from_user.id)
            except: pass

def vc_enabled():
    return get_status()

@vc_app.on_raw_update()
async def vc_handler(client, update, users, chats):
    global LAST
    if not vc_enabled(): return
    try:
        if hasattr(update, "participants"):
            for gid in GROUPS:
                actions = []
                for p in update.participants:
                    if not hasattr(p.peer, "user_id"): continue
                    uid = p.peer.user_id
                    try:
                        m = await client.get_chat_member(gid, uid)
                        role = m.status
                    except: role = "none"
                    if role in ["administrator", "creator"]: continue
                    mute = False
                    if role != "member": mute = True
                    if hasattr(p.peer, "channel_id"): mute = True
                    if hasattr(p, "video") and p.video: mute = True
                    now = time.time()
                    MIC_TRACK[uid].append(now)
                    MIC_TRACK[uid] = [t for t in MIC_TRACK[uid] if now - t < 5]
                    if len(MIC_TRACK[uid]) > 5: mute = True
                    actions.append((p.peer, mute))
                if actions and time.time() - LAST > COOLDOWN:
                    LAST = time.time()
                    await client.invoke(JoinGroupCall(call=update.call, join_as=await client.resolve_peer("me"), params=b'{"muted": true}'))
                    for peer, mute in actions:
                        await client.invoke(EditGroupCallParticipant(call=update.call, participant=peer, muted=mute))
                    await asyncio.sleep(0.3)
                    await client.invoke(LeaveGroupCall(call=update.call))
    except Exception as e:
        print(e)

# ================= MAIN =================
def run_panel():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    print("🤖 UI BOT RUNNING")
    app.run_polling()

def run_vc():
    print("🔥 GOD VC ENGINE RUNNING")
    vc_app.run()

# ================= RUN BOTH =================
import threading
threading.Thread(target=run_vc).start()
run_panel()