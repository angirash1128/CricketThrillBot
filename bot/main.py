import os
import time
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import TeleBot, types
from match_engine import get_live_ipl_match, debug_ipl_status

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing!")

bot = TeleBot(TOKEN)

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
    print(f"Web server running on port {port}")
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
# HANDLERS
# ─────────────────────────────────────────

@bot.message_handler(commands=["start"])
def start_cmd(message):
    name = message.from_user.first_name or "Cricket Fan"
    print(f"/start from {message.from_user.id}")

    bot.send_message(
        message.chat.id,
        f"🏏 Welcome <b>{name}</b>!\n\n"
        f"Tap below to check IPL match.\n\n"
        f"Debug command: /debuglive",
        reply_markup=get_menu(),
        parse_mode="HTML"
    )


@bot.message_handler(commands=["debuglive"])
def debug_live_cmd(message):
    print(f"/debuglive from {message.from_user.id}")
    report = debug_ipl_status()

    bot.send_message(
        message.chat.id,
        f"🔍 <b>IPL Debug Report</b>\n\n<code>{report}</code>",
        parse_mode="HTML"
    )


@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def live_match_handler(message):
    print(f"Live IPL Match button from {message.from_user.id}")
    match = get_live_ipl_match()

    if not match:
        bot.send_message(
            message.chat.id,
            "❌ No live IPL match right now.\n"
            "I will alert you when match starts! 🔔\n\n"
            "Send /debuglive to inspect API."
        )
        return

    bot.send_message(
        message.chat.id,
        f"🏏 <b>{match['team1']}</b> vs <b>{match['team2']}</b>\n\n"
        f"📊 Status: {match['status']}\n"
        f"🧭 State: {match['state']}\n"
        f"🏆 Series: {match['series_name']}",
        parse_mode="HTML"
    )


@bot.message_handler(func=lambda m: True)
def catch_all(message):
    print(f"Catch all: {message.text}")
    bot.send_message(
        message.chat.id,
        "Tap the button below 👇",
        reply_markup=get_menu()
    )

# ─────────────────────────────────────────
# START
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("Starting Thrill Alert Bot...")

    # Web server
    threading.Thread(target=run_server, daemon=True).start()

    # Webhook force clear
    try:
        requests.get(
            f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true",
            timeout=10
        )
        print("Webhook cleared")
    except Exception as e:
        print(f"Webhook clear error: {e}")

    time.sleep(2)

    print("Bot polling started...")
    bot.polling(none_stop=True, timeout=30, interval=1)
