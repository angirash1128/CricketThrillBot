import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import TeleBot, types
from match_engine import get_live_ipl_match

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = TeleBot(TOKEN, skip_pending=True)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Thrill Alert Bot is Running")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), SimpleHandler).serve_forever()

@bot.message_handler(commands=["start"])
def start_cmd(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🏏 Live IPL Match")
    bot.send_message(message.chat.id, "🏏 <b>Thrill Alert Active!</b>\n\nTap below to check today's IPL game.", reply_markup=kb, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def live_match(message):
    match = get_live_ipl_match()
    if not match:
        bot.send_message(message.chat.id, "❌ <b>No live IPL match found right now.</b>\n\nI will notify you automatically when the match starts! 🔔", parse_mode="HTML")
        return

    bot.send_message(message.chat.id, f"🏏 <b>{match['team1']}</b> vs <b>{match['team2']}</b>\n\n📊 Status: {match['status']}\n\nI am monitoring this match for wickets and thrills! 🚨", parse_mode="HTML")

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    print("✅ Bot is Starting...")
    bot.infinity_polling()
