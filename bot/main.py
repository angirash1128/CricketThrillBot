import os
import time
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import TeleBot, types
from match_engine import (
    get_live_ipl_match,
    get_match_scorecard,
    parse_current_innings,
    detect_thrills
)

# ─────────────────────────────────────────
# BOT SETUP
# ─────────────────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing!")

bot = TeleBot(TOKEN)

# ─────────────────────────────────────────
# WEB SERVER (Render ke liye zaroori)
# ─────────────────────────────────────────

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Thrill Alert Bot is Running!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    print(f"✅ Web server on port {port}")
    server.serve_forever()

# ─────────────────────────────────────────
# STATE
# ─────────────────────────────────────────

current_match = {"match_id": None, "team1": None, "team2": None}
sos_state = {}

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def get_menu():
    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        is_persistent=True
    )
    kb.row("🏏 Live IPL Match", "⭐ Give Feedback")
    kb.row("⚙️ Settings", "📢 Share Bot")
    kb.row("❓ Help")
    return kb

def broadcast(text):
    from database import get_all_active_users
    users = get_all_active_users()
    for user in users:
        try:
            bot.send_message(
                user["user_id"],
                text,
                parse_mode="HTML"
            )
            time.sleep(0.05)
        except Exception as e:
            print(f"Broadcast fail {user['user_id']}: {e}")

# ─────────────────────────────────────────
# BOT HANDLERS
# ─────────────────────────────────────────

@bot.message_handler(commands=["start"])
def start_cmd(message):
    from database import (
        user_exists, is_setup_complete,
        create_user, update_last_active
    )
    uid = message.from_user.id
    name = message.from_user.first_name or "Cricket Fan"

    if user_exists(uid):
        update_last_active(uid)

    if user_exists(uid) and is_setup_complete(uid):
        bot.send_message(
            uid,
            f"🏏 Welcome back <b>{name}</b>!\n\n"
            f"IPL 2026 Thrill Alerts are active. 🔔",
            reply_markup=get_menu(),
            parse_mode="HTML"
        )
        return

    create_user(uid, name)

    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton(
        "🔔 Set Up Alerts", callback_data="setup_start"))

    bot.send_message(
        uid,
        f"🏏 <b>Welcome to Thrill Alert!</b>\n\n"
        f"Hi <b>{name}</b>! 👋\n\n"
        f"I will alert you ONLY when something\n"
        f"EXCITING happens in IPL 2026!\n\n"
        f"• 🚨 Wickets\n"
        f"• 😱 Batting Collapse\n"
        f"• ⚡ Momentum Shift\n"
        f"• 🔴 Thriller Finish\n"
        f"• 🔥 Super Over\n\n"
        f"Tap below to get started!",
        reply_markup=kb,
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def live_match_btn(message):
    match = get_live_ipl_match()
    if not match:
        bot.send_message(
            message.chat.id,
            "🏏 <b>No live IPL match right now.</b>\n\n"
            "I will automatically alert you\n"
            "when something exciting happens! 🔔",
            parse_mode="HTML"
        )
        return
    bot.send_message(
        message.chat.id,
        f"🏏 <b>Live IPL Match</b>\n\n"
        f"<b>{match['team1']}</b> vs <b>{match['team2']}</b>\n\n"
        f"📊 {match['status']}\n\n"
        f"I am watching for thrills! 👀",
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: m.text == "❓ Help")
def help_btn(message):
    bot.send_message(
        message.chat.id,
        "❓ <b>How Thrill Alert Works</b>\n\n"
        "I do NOT send every ball update.\n\n"
        "I ONLY alert you when:\n"
        "• 🚨 A wicket falls\n"
        "• 😱 Batting collapses\n"
        "• ⚡ Massive momentum shift\n"
        "• 🔴 Match goes to wire\n"
        "• 🔥 Super Over\n\n"
        "So your phone only buzzes when\n"
        "something ACTUALLY matters! 🏏",
        reply_markup=get_menu(),
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: m.text == "📢 Share Bot")
def share_btn(message):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton(
        "📤 Share on Telegram",
        url="https://t.me/share/url?url=https://t.me/Cricket_Thrill_Alert_Bot"
    ))
    bot.send_message(
        message.chat.id,
        "📢 <b>Share Thrill Alert!</b>\n\n"
        "Never miss a match-turning moment!\n\n"
        "👉 @Cricket_Thrill_Alert_Bot",
        reply_markup=kb,
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: True)
def catch_all(message):
    bot.send_message(
        message.chat.id,
        "Use the menu below 👇",
        reply_markup=get_menu()
    )

# ─────────────────────────────────────────
# SMART THRILL POLLING LOOP
# ─────────────────────────────────────────

def match_poll_loop():
    print("🚀 Thrill Hunter Started")

    while True:
        try:
            now = datetime.now()
            hour = now.hour

            # API SLEEP: 12 AM to 3 PM (zero API calls)
            if 0 <= hour < 15:
                print("😴 Sleeping - saving API quota")
                time.sleep(3600)
                continue

            # Get live match
            match = get_live_ipl_match()

            if not match:
                # Check every 30 min when no match
                print("🔍 No match - checking in 30 min")
                time.sleep(1800)
                continue

            mid = match["match_id"]

            # New match announcement
            if current_match["match_id"] != mid:
                current_match["match_id"] = mid
                current_match["team1"] = match["team1"]
                current_match["team2"] = match["team2"]
                print(f"🏏 Match: {match['team1']} vs {match['team2']}")
                broadcast(
                    f"🏏 <b>Match Starting!</b>\n\n"
                    f"<b>{match['team1']}</b> vs "
                    f"<b>{match['team2']}</b>\n\n"
                    f"I am now watching for THRILLS! 👀\n"
                    f"You will be alerted when something "
                    f"exciting happens!"
                )

            # Get scorecard
            scard = get_match_scorecard(mid)
            data = parse_current_innings(scard)

            if data:
                # Smart polling speed based on match situation
                overs = data["overs"]
                innings = data["innings_id"]

                # Last 4 overs of any innings = fast poll
                if overs >= 16.0:
                    wait = 180  # 3 min
                # 2nd innings last 8 overs = medium poll
                elif innings == 2 and overs >= 12.0:
                    wait = 300  # 5 min
                # Normal game = slow poll (save API)
                else:
                    wait = 600  # 10 min

                # Detect thrills
                alerts = detect_thrills(mid, data)

                for alert in alerts:
                    print(f"🎯 Thrill: {alert['type']}")
                    broadcast(alert["message"])

                print(f"⏱️ Next check in {wait//60} min")
                time.sleep(wait)
            else:
                time.sleep(600)

        except Exception as e:
            print(f"❌ Poll error: {e}")
            time.sleep(300)

# ─────────────────────────────────────────
# START
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("🏏 Thrill Alert Bot Starting...")

    # Web server (Render ke liye)
    threading.Thread(target=run_server, daemon=True).start()

    # Database setup
    from database import setup_database
    setup_database()

    # Match polling
    threading.Thread(target=match_poll_loop, daemon=True).start()

    print("✅ Bot is LIVE!")

    # Clear old connections
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

    bot.polling(none_stop=True, timeout=30)
