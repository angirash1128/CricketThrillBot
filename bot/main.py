import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import TeleBot, types
from match_engine import get_live_ipl_match

# Bot setup
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing!")

bot = TeleBot(TOKEN)

# ─────────────────────────────────────────
# WEB SERVER
# ─────────────────────────────────────────

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Thrill Alert Running")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# ─────────────────────────────────────────
# MENU
# ─────────────────────────────────────────

def main_menu():
    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        is_persistent=True
    )
    kb.row("🏏 Live IPL Match")
    kb.row("⚙️ Settings", "⭐ Give Feedback")
    return kb

# ─────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────

@bot.message_handler(commands=["start"])
def start_cmd(message):
    print(f"User {message.from_user.id} sent /start")
    bot.send_message(
        message.chat.id,
        f"🏏 Welcome to Thrill Alert!\n\n"
        f"Hi {message.from_user.first_name}! 👋\n\n"
        f"Tap below to check today's IPL match.",
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def live_match(message):
    print(f"User {message.from_user.id} tapped Live Match")
    match = get_live_ipl_match()

    if not match:
        bot.send_message(
            message.chat.id,
            "❌ No live IPL match right now.\n\n"
            "I will alert you when match starts! 🔔"
        )
        return

    bot.send_message(
        message.chat.id,
        f"🏏 <b>{match['team1']}</b> vs <b>{match['team2']}</b>\n\n"
        f"📊 Status: {match['status']}",
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: True)
def catch_all(message):
    print(f"Message from {message.from_user.id}: {message.text}")
    bot.send_message(
        message.chat.id,
        "Tap the button below 👇",
        reply_markup=main_menu()
    )

# ─────────────────────────────────────────
# START
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("Starting Thrill Alert Bot...")

    # Web server
    threading.Thread(target=run_server, daemon=True).start()
    print("Web server started")

    # Clear old connections
    try:
        bot.delete_webhook(drop_pending_updates=True)
        print("Webhook cleared")
    except Exception as e:
        print(f"Webhook clear: {e}")

    print("Bot polling started...")
    bot.polling(none_stop=True, timeout=30)
