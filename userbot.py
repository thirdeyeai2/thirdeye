import os
import json
import asyncio
import time
from collections import defaultdict
from pyrogram import Client
from pyrogram.raw.functions.phone import JoinGroupCall, LeaveGroupCall, EditGroupCallParticipant
from config import API_ID, API_HASH, GROUPS

app = Client(
    "vc_god",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=os.getenv("SESSION_STRING")
)

LAST = 0
COOLDOWN = 2
MIC_TRACK = defaultdict(list)

BAD_WORDS = ["porn", "sex", "xxx", "nude"]

def is_enabled():
    with open("status.json") as f:
        return json.load(f)["vc"]

# ===== BAD WORD FILTER =====
@app.on_message()
async def filter_msg(client, msg):
    if not msg.text:
        return

    text = msg.text.lower()

    for w in BAD_WORDS:
        if w in text:
            try:
                await client.kick_chat_member(msg.chat.id, msg.from_user.id)
            except:
                pass

# ===== VC CONTROL =====
@app.on_raw_update()
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

                    # mic spam
                    now = time.time()
                    MIC_TRACK[uid].append(now)
                    MIC_TRACK[uid] = [t for t in MIC_TRACK[uid] if now - t < 5]

                    if len(MIC_TRACK[uid]) > 5:
                        mute = True

                    actions.append((p.peer, mute))

                if actions and time.time() - LAST > COOLDOWN:

                    LAST = time.time()

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
        print(e)

print("🔥 GOD VC ENGINE RUNNING")
app.run()