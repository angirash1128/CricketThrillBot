import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import TeleBot, types
from match_engine import get_live_ipl_match

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing")

bot = TeleBot(TOKEN)

# ─────────────────────────────────────────
# WEB SERVER (Render Free Tier)
# ─────────────────────────────────────────

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Thrill Alert Running")

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
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🏏 Live IPL Match")
    return kb

# ─────────────────────────────────────────
# COMMANDS
# ─────────────────────────────────────────

@bot.message_handler(commands=["start"])
def start_cmd(message):
    bot.send_message(
        message.chat.id,
        "🏏 Welcome to Thrill Alert!\n\nTap below to check IPL match.",
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def live_match(message):
    match = get_live_ipl_match()

    if not match:
        bot.send_message(
            message.chat.id,
            "❌ No live IPL match found right now."
        )
        return

    bot.send_message(
        message.chat.id,
        f"🏏 {match['team1']} vs {match['team2']}\n\nStatus: {match['status']}"
    )

# ─────────────────────────────────────────
# POLLING LOOP (Safe Mode - 10 min)
# ─────────────────────────────────────────

def match_poll_loop():
    print("✅ Polling Started")

    while True:
        try:
            match = get_live_ipl_match()
            if match:
                print("Match Found:", match["team1"], "vs", match["team2"])
            else:
                print("No match detected")

            time.sleep(600)  # 10 minutes

        except Exception as e:
            print("Polling error:", e)
            time.sleep(300)

# ─────────────────────────────────────────
# START BOT
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("Cleaning old webhook...")
    bot.remove_webhook()

    threading.Thread(target=run_server, daemon=True).start()
    threading.Thread(target=match_poll_loop, daemon=True).start()

    print("✅ Bot Starting Fresh...")
    bot.infinity_polling(skip_pending=True)
