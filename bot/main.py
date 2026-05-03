import os
import time
import threading
import requests as req
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import TeleBot, types
from match_engine import (
    get_live_ipl_match,
    debug_ipl_status,
    get_match_scorecard,
    parse_current_innings,
    detect_thrills
)
from ipl_schedule import is_match_time_now, get_todays_matches

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing!")

bot = TeleBot(TOKEN)

alert_users = set()
current_match = {"match_id": None}

# ─────────────────────────────────────────
# WEB SERVER
# ─────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Thrill Alert Running")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Web server on port {port}")
    server.serve_forever()

# ─────────────────────────────────────────
# MENU
# ─────────────────────────────────────────

def get_menu():
    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        is_persistent=True
    )
    kb.row("🏏 Live IPL Match")
    kb.row("📅 Today's Schedule")
    return kb

# ─────────────────────────────────────────
# BROADCAST
# ─────────────────────────────────────────

def broadcast(text):
    for uid in list(alert_users):
        try:
            bot.send_message(uid, text, parse_mode="HTML")
            time.sleep(0.05)
        except Exception:
            pass

# ─────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────

@bot.message_handler(commands=["start"])
def start_cmd(message):
    uid = message.from_user.id
    name = message.from_user.first_name or "Fan"
    alert_users.add(uid)

    today = get_todays_matches()
    if today:
        schedule_text = "\n".join(
            [f"• {m['team1']} vs {m['team2']} at {m['hour']}:{m['minute']:02d}"
             for m in today]
        )
    else:
        schedule_text = "No IPL match today"

    bot.send_message(
        message.chat.id,
        f"🏏 <b>Welcome to Thrill Alert!</b>\n\n"
        f"Hi <b>{name}</b>! 👋\n\n"
        f"📅 <b>Today's IPL:</b>\n{schedule_text}\n\n"
        f"✅ You will get automatic THRILL alerts!\n"
        f"I only buzz when something EXCITING happens!\n\n"
        f"Debug: /debuglive",
        reply_markup=get_menu(),
        parse_mode="HTML"
    )


@bot.message_handler(func=lambda m: m.text == "📅 Today's Schedule")
def schedule_handler(message):
    alert_users.add(message.from_user.id)

    today = get_todays_matches()
    if today:
        text = "\n".join(
            [f"• <b>{m['team1']}</b> vs <b>{m['team2']}</b> at {m['hour']}:{m['minute']:02d}"
             for m in today]
        )
    else:
        text = "No IPL match scheduled today"

    bot.send_message(
        message.chat.id,
        f"📅 <b>Today's IPL Schedule</b>\n\n{text}",
        parse_mode="HTML"
    )


@bot.message_handler(commands=["debuglive"])
def debug_cmd(message):
    alert_users.add(message.from_user.id)
    report = debug_ipl_status()
    bot.send_message(
        message.chat.id,
        f"🔍 <b>Debug</b>\n\n<code>{report}</code>",
        parse_mode="HTML"
    )


@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def live_match_handler(message):
    alert_users.add(message.from_user.id)

    match = get_live_ipl_match()
    if not match:
        bot.send_message(
            message.chat.id,
            "❌ No live IPL match right now.\n\n"
            "I will auto-alert when thrills happen! 🔔"
        )
        return

    bot.send_message(
        message.chat.id,
        f"🏏 <b>{match['team1']}</b> vs <b>{match['team2']}</b>\n\n"
        f"📊 {match['status']}\n\n"
        f"✅ Thrill alerts are ON!",
        parse_mode="HTML"
    )


@bot.message_handler(func=lambda m: True)
def catch_all(message):
    alert_users.add(message.from_user.id)
    bot.send_message(
        message.chat.id,
        "Tap below 👇",
        reply_markup=get_menu()
    )

# ─────────────────────────────────────────
# SMART THRILL POLLING LOOP
# ─────────────────────────────────────────

def thrill_poll_loop():
    print("🚀 Smart Thrill Engine Started")

    while True:
        try:
            now = datetime.now()

            # STEP 1: Match time hai ya nahi?
            if not is_match_time_now():
                # No match window - sleep 30 min
                # ZERO API calls
                hour = now.hour
                if 8 <= hour <= 14:
                    print(f"😴 No match window - sleep 1 hour")
                    time.sleep(3600)
                else:
                    print(f"😴 No match window - sleep 30 min")
                    time.sleep(1800)
                continue

            # STEP 2: Match time hai - API call karo
            match = get_live_ipl_match()

            if not match:
                print("Match window but no live match yet - check in 15 min")
                time.sleep(900)
                continue

            mid = match["match_id"]

            # New match announcement
            if current_match["match_id"] != mid:
                current_match["match_id"] = mid
                print(f"🏏 {match['team1']} vs {match['team2']}")
                broadcast(
                    f"🏏 <b>Match Alert!</b>\n\n"
                    f"<b>{match['team1']}</b> vs "
                    f"<b>{match['team2']}</b>\n\n"
                    f"Monitoring for THRILLS! 👀"
                )

            # STEP 3: Scorecard check
            scard = get_match_scorecard(mid)
            data = parse_current_innings(scard)

            if data:
                overs = data["overs"]
                wickets = data["wickets"]
                innings_id = data["innings_id"]
                target = data.get("target")

                # Detect thrills
                alerts = detect_thrills(mid, data)
                for alert in alerts:
                    print(f"🎯 {alert['type']}")
                    broadcast(alert["message"])

                # STEP 4: SMART POLLING SPEED
                # Normal game = slow (save API)
                # Thriller zone = fast

                if innings_id == 2 and target:
                    runs_needed = target - data["runs"]
                    balls_left = max(1, int((20 - overs) * 6))

                    # SUPER THRILLER: last 3 overs, close
                    if overs >= 17.0 and 0 < runs_needed <= 30:
                        wait = 120  # 2 min
                        print(f"🔥 THRILLER MODE - 2 min poll")

                    # THRILLER ZONE: last 5 overs
                    elif overs >= 15.0 and 0 < runs_needed <= 50:
                        wait = 300  # 5 min
                        print(f"🔴 CLOSE CHASE - 5 min poll")

                    # Normal 2nd innings
                    else:
                        wait = 600  # 10 min
                        print(f"⏱️ Normal chase - 10 min poll")

                # 1st innings
                elif innings_id == 1:
                    if wickets >= 5:
                        wait = 300  # 5 min - collapse possible
                        print(f"⚠️ Wickets falling - 5 min poll")
                    elif overs >= 16.0:
                        wait = 300  # 5 min - death overs
                        print(f"💥 Death overs - 5 min poll")
                    else:
                        wait = 1200  # 20 min normal
                        print(f"😎 Normal batting - 20 min poll")

                else:
                    wait = 600

            else:
                wait = 900  # 15 min if no scorecard

            time.sleep(wait)

        except Exception as e:
            print(f"Poll error: {e}")
            time.sleep(600)

# ─────────────────────────────────────────
# START
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("Starting Thrill Alert Bot...")

    # Web server
    threading.Thread(target=run_server, daemon=True).start()

    # Webhook clear
    try:
        req.get(
            f"https://api.telegram.org/bot{TOKEN}"
            f"/deleteWebhook?drop_pending_updates=true",
            timeout=10
        )
        print("Webhook cleared")
    except Exception:
        pass

    time.sleep(2)

    # Smart Thrill Engine
    threading.Thread(target=thrill_poll_loop, daemon=True).start()
    print("Smart Thrill Engine started")

    print("Bot polling started...")
    bot.polling(none_stop=True, timeout=30, interval=1)
