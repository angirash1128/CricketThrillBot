# main.py
# Thrill Alert Bot - Saver Mode Edition

import os
import time
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

import telebot
from telebot import types

from database import (
    setup_database, user_exists, is_setup_complete,
    create_user, update_user_field, complete_setup,
    get_user, get_all_active_users,
    stop_notifications, resume_notifications, update_last_active
)
from feedback_sheet import setup_sheet_headers, save_feedback
from match_engine import (
    get_live_ipl_match,
    get_match_scorecard,
    parse_current_innings,
    detect_thrills
)

# ─────────────────────────────────────────
# WEB SERVER (For Render Free Tier)
# ─────────────────────────────────────────

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Thrill Alert Bot is running!")

    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# ─────────────────────────────────────────
# BOT SETUP
# ─────────────────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing!")

bot = telebot.TeleBot(TOKEN, skip_pending=True)

# ─────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────

WHATSAPP_LINK = "https://whatsapp.com/channel/0029VbCxEWIKwqSaq8lHO517"
TONE_FILE_PATH = os.path.join(os.path.dirname(__file__), "thrill_alert_tone.mp3")

IPL_TEAMS = [
    "Mumbai Indians 🔵", "Chennai Super Kings 🟡", "Royal Challengers Bengaluru 🔴",
    "Kolkata Knight Riders 🟣", "Delhi Capitals 🔵", "Punjab Kings 🔴",
    "Rajasthan Royals 🩷", "Sunrisers Hyderabad 🟠", "Gujarat Titans 🔵",
    "Lucknow Super Giants 🩵"
]

ALERT_OPTIONS = ["Only My Team Matches", "All IPL Matches", "Big Matches Only"]

# ─────────────────────────────────────────
# STATE VARIABLES
# ─────────────────────────────────────────

sos_state = {}
current_match = {"match_id": None, "team1": None, "team2": None}
user_states = {}
feedback_temp = {}

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def get_bottom_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
    keyboard.row("🏏 Live IPL Match", "⭐ Give Feedback")
    keyboard.row("⚙️ Settings", "📢 Share Bot")
    keyboard.row("❓ Help")
    return keyboard

def broadcast_message(text, reply_markup=None):
    users = get_all_active_users()
    for user in users:
        try:
            bot.send_message(user["user_id"], text, reply_markup=reply_markup, parse_mode="HTML")
            time.sleep(0.05)
        except Exception: pass

def start_sos_for_all(alert_message):
    users = get_all_active_users()
    for user in users:
        sos_state[user["user_id"]] = {"message": alert_message, "count": 0, "active": True}

    def sos_loop():
        for _ in range(5):
            time.sleep(30)
            for uid in list(sos_state.keys()):
                st = sos_state.get(uid)
                if st and st["active"] and st["count"] < 5:
                    try:
                        kb = types.InlineKeyboardMarkup()
                        kb.add(types.InlineKeyboardButton("✅ I am Watching", callback_data="sos_watching"))
                        bot.send_message(uid, st["message"], reply_markup=kb, parse_mode="HTML")
                        st["count"] += 1
                    except Exception: pass
    threading.Thread(target=sos_loop, daemon=True).start()

# ─────────────────────────────────────────
# COMMAND HANDLERS (/start, /stop, /resume)
# ─────────────────────────────────────────

@bot.message_handler(commands=["start"])
def handle_start(message):
    uid = message.from_user.id
    name = message.from_user.first_name or "Cricket Fan"
    if user_exists(uid):
        update_last_active(uid)
        if is_setup_complete(uid):
            bot.send_message(uid, f"🏏 Welcome back, <b>{name}</b>!\nAlerts are active. 🔔", reply_markup=get_bottom_menu(), parse_mode="HTML")
            return
    create_user(uid, name)
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("🔔 Set Up My Alerts", callback_data="setup_start"))
    bot.send_message(uid, f"🏏 <b>Welcome to Thrill Alert!</b>\n\nNever miss an exciting IPL moment! ⚡", reply_markup=kb, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def handle_live_btn(message):
    match = get_live_ipl_match()
    if not match:
        bot.send_message(message.chat.id, "🏏 <b>No live IPL match right now.</b>\nI'll alert you when it starts! 🔔", parse_mode="HTML")
        return
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("🔔 Get Alerts", callback_data=f"subscribe_{match['match_id']}"))
    bot.send_message(message.chat.id, f"🏏 <b>Live IPL Match</b>\n\n<b>{match['team1']}</b> vs <b>{match['team2']}</b>\nStatus: {match['status']}", reply_markup=kb, parse_mode="HTML")

# ─────────────────────────────────────────
# CALLBACK HANDLERS (Onboarding, Settings, Tone)
# ─────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "setup_start")
def setup_step1(call):
    bot.answer_callback_query(call.id)
    kb = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(t, callback_data=f"team_{i}") for i, t in enumerate(IPL_TEAMS)]
    kb.add(*buttons)
    bot.edit_message_text("🏏 <b>Step 1: Choose Your Team</b> 👇", call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="HTML")

@bot.callback_query_handler(func=lambda c: c.data.startswith("team_"))
def setup_step2(call):
    idx = int(call.data.split("_")[1])
    update_user_field(call.from_user.id, "favorite_team", IPL_TEAMS[idx])
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("🏏 My Team Only", callback_data="pref_0"),
           types.InlineKeyboardButton("🌐 All IPL Matches", callback_data="pref_1"))
    bot.edit_message_text("🔔 <b>Step 2: Alert Preference</b> 👇", call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="HTML")

@bot.callback_query_handler(func=lambda c: c.data.startswith("pref_"))
def setup_finish(call):
    idx = int(call.data.split("_")[1])
    update_user_field(call.from_user.id, "alert_preference", ALERT_OPTIONS[idx])
    complete_setup(call.from_user.id)
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("🎵 Set Tone", callback_data="tone_setup"))
    kb.row(types.InlineKeyboardButton("📱 WhatsApp", url=WHATSAPP_LINK))
    bot.edit_message_text("🎉 <b>Setup Complete!</b>\nDon't forget to set your Alert Tone. 👇", call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="HTML")
    bot.send_message(call.from_user.id, "Use the menu below to explore!", reply_markup=get_bottom_menu())

@bot.callback_query_handler(func=lambda c: c.data == "tone_setup")
def handle_tone(call):
    try:
        with open(TONE_FILE_PATH, "rb") as f:
            bot.send_document(call.message.chat.id, f, caption="📥 Download this file and set it as your bot notification sound!")
    except Exception: bot.send_message(call.message.chat.id, "⚠️ Tone file not found!")

@bot.callback_query_handler(func=lambda c: c.data == "sos_watching")
def sos_stop(call):
    if call.from_user.id in sos_state: sos_state[call.from_user.id]["active"] = False
    bot.answer_callback_query(call.id, "✅ Enjoy the match!")

# ─────────────────────────────────────────
# SMART MATCH POLLING LOOP (Saver Mode)
# ─────────────────────────────────────────

def match_poll_loop():
    print("🚀 Smart Saver Polling Loop Started")
    while True:
        try:
            now = datetime.now()
            hour = now.hour
            
            # 1. API SLEEP (Raat 12 AM se Dopahar 3 PM tak band)
            if hour >= 0 and hour < 15:
                print("😴 Saver Mode: API Sleeping (Zero calls)")
                time.sleep(1800) # 30 min baad loop check karo
                continue

            # 2. DISCOVERY (Match dhundo)
            match = get_live_ipl_match()
            if not match:
                print("🔍 Saver Mode: No IPL match. Checking in 30 mins...")
                time.sleep(1800)
                continue

            # 3. MATCH FOUND
            mid = match["match_id"]
            if current_match["match_id"] != mid:
                current_match["match_id"] = mid
                broadcast_message(f"🏏 <b>Match Alert!</b>\n\n<b>{match['team1']}</b> vs <b>{match['team2']}</b>\nMonitoring ON! 🔥")

            # 4. TRACKING
            scard = get_match_scorecard(mid)
            data = parse_current_innings(scard)
            if data:
                alerts = detect_thrills(mid, data)
                for a in alerts:
                    if a["is_mega"]: start_sos_for_all(a["message"])
                    else: broadcast_message(a["message"])

            # LIVE MODE: Har 10 minute mein sirf 1 call (Quota Saving)
            print("🏏 Match Live: Polling again in 10 minutes")
            time.sleep(600)

        except Exception as e:
            print(f"❌ Poll error: {e}")
            time.sleep(300)

# ─────────────────────────────────────────
# MAIN START
# ─────────────────────────────────────────

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    setup_database()
    setup_sheet_headers()
    threading.Thread(target=match_poll_loop, daemon=True).start()
    print("✅ Thrill Alert Bot is LIVE!")
    bot.infinity_polling(timeout=60)
