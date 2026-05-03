import os
import time
import threading
import requests as req
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import TeleBot, types
from match_engine import (
    get_live_ipl_match,
    debug_ipl_status,
    get_match_scorecard,
    parse_current_innings,
    detect_thrills
)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing!")

bot = TeleBot(TOKEN)

# Subscribed users
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
    print(f"/start from {uid}")
    bot.send_message(
        message.chat.id,
        f"🏏 Welcome <b>{name}</b>!\n\n"
        f"✅ You will get automatic THRILL alerts!\n\n"
        f"Tap below to check match.\n"
        f"Debug: /debuglive",
        reply_markup=get_menu(),
        parse_mode="HTML"
    )

@bot.message_handler(commands=["debuglive"])
def debug_cmd(message):
    alert_users.add(message.from_user.id)
    report = debug_ipl_status()
    bot.send_message(
        message.chat.id,
        f"🔍 <b>Debug Report</b>\n\n<code>{report}</code>",
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def live_match_handler(message):
    uid = message.from_user.id
    alert_users.add(uid)
    print(f"Live button from {uid}")

    match = get_live_ipl_match()

    if not match:
        bot.send_message(
            message.chat.id,
            "❌ No live IPL match right now.\n\n"
            "Send /debuglive to inspect API."
        )
        return

    bot.send_message(
        message.chat.id,
        f"🏏 <b>{match['team1']}</b> vs <b>{match['team2']}</b>\n\n"
        f"📊 {match['status']}\n"
        f"🧭 State: {match['state']}\n\n"
        f"✅ You will get automatic THRILL alerts!",
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
# THRILL POLLING LOOP
# ─────────────────────────────────────────

def thrill_poll_loop():
    print("🚀 Thrill Polling Started")

    while True:
        try:
            match = get_live_ipl_match()

            if not match:
                print("No match - sleep 10 min")
                time.sleep(600)
                continue

            mid = match["match_id"]

            # New match announcement
            if current_match["match_id"] != mid:
                current_match["match_id"] = mid
                print(f"New match: {match['team1']} vs {match['team2']}")
                broadcast(
                    f"🏏 <b>Match Alert!</b>\n\n"
                    f"<b>{match['team1']}</b> vs "
                    f"<b>{match['team2']}</b>\n\n"
                    f"Monitoring for THRILLS! 👀"
                )

            # Scorecard
            scard = get_match_scorecard(mid)
            data = parse_current_innings(scard)

            if data:
                overs = data["overs"]
                innings = data["innings_id"]

                alerts = detect_thrills(mid, data)
                for alert in alerts:
                    print(f"THRILL: {alert['type']}")
                    broadcast(alert["message"])

                # Smart polling
                if overs >= 16.0:
                    wait = 120   # 2 min - last 4 overs
                elif innings == 2 and overs >= 12.0:
                    wait = 180   # 3 min
                else:
                    wait = 600   # 10 min normal
            else:
                wait = 600

            print(f"Next check in {wait//60} min")
            time.sleep(wait)

        except Exception as e:
            print(f"Poll error: {e}")
            time.sleep(300)

# ─────────────────────────────────────────
# START
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("Starting Thrill Alert Bot...")

    threading.Thread(target=run_server, daemon=True).start()

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

    threading.Thread(target=thrill_poll_loop, daemon=True).start()
    print("Thrill polling started")

    print("Bot polling started...")
    bot.polling(none_stop=True, timeout=30, interval=1)
