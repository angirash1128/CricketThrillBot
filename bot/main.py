import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import TeleBot, types
from match_engine import get_live_ipl_match

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TOKEN missing!")

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
    bot.send_message(
        message.chat.id,
        f"🏏 Welcome <b>{name}</b>!\n\n"
        f"Tap below to check IPL match.",
        reply_markup=get_menu(),
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def live_match(message):
    match = get_live_ipl_match()
    if not match:
        bot.send_message(
            message.chat.id,
            "❌ No live IPL match right now.\n"
            "I will alert you when match starts! 🔔"
        )
        return
    bot.send_message(
        message.chat.id,
        f"🏏 <b>{match['team1']}</b> vs <b>{match['team2']}</b>\n\n"
        f"Status: {match['status']}",
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: True)
def catch_all(message):
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

    # Web server start karo
    threading.Thread(target=run_server, daemon=True).start()

    # Webhook clear karo
    try:
        import requests as req
        req.get(
            f"https://api.telegram.org/bot{TOKEN}"
            f"/deleteWebhook?drop_pending_updates=true",
            timeout=10
        )
        print("Webhook cleared")
    except Exception:
        pass

    time.sleep(2)

    print("Bot polling started...")
    bot.polling(none_stop=True, timeout=30, interval=1)
