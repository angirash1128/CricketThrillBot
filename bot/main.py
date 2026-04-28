import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import TeleBot, types
from match_engine import get_live_ipl_match

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing")

bot = TeleBot(TOKEN, skip_pending=True)

# ─────────────────────────────────────────
# WEB SERVER (Render Free)
# ─────────────────────────────────────────

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Thrill Alert running")

    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# ─────────────────────────────────────────
# BOT MENU
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
        "🏏 Welcome to Thrill Alert!\n\nTap below to check live IPL match.",
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def live_match(message):
    match = get_live_ipl_match()

    if not match:
        bot.send_message(
            message.chat.id,
            "❌ No live IPL match detected right now."
        )
        return

    bot.send_message(
        message.chat.id,
        f"🏏 <b>{match['team1']}</b> vs <b>{match['team2']}</b>\n\n"
        f"Status: {match['status']}",
        parse_mode="HTML"
    )

# ─────────────────────────────────────────
# POLLING LOOP (10 min safe mode)
# ─────────────────────────────────────────

def match_poll_loop():
    print("✅ Polling Started (10 min mode)")
    while True:
        try:
            match = get_live_ipl_match()
            if match:
                print("MATCH FOUND:", match["team1"], "vs", match["team2"])
            else:
                print("No IPL match")

            time.sleep(600)  # 10 minutes safe for quota

        except Exception as e:
            print("Polling error:", e)
            time.sleep(300)

# ─────────────────────────────────────────
# START
# ─────────────────────────────────────────

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    threading.Thread(target=match_poll_loop, daemon=True).start()
    bot.infinity_polling()
