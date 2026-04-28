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
        self.wfile.write(b"Bot is Running")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), SimpleHandler).serve_forever()

@bot.message_handler(commands=["start"])
def start_cmd(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🏏 Live IPL Match")
    bot.send_message(message.chat.id, "🏏 Thrill Alert Ready!\nClick below to test.", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def live_match(message):
    print("User clicked Live Match button")
    match = get_live_ipl_match()
    
    if not match:
        bot.send_message(message.chat.id, "❌ Match detection failed even with complete matches. Check logs.")
        return

    bot.send_message(message.chat.id, f"🏏 {match['team1']} vs {match['team2']}\nStatus: {match['status']}\n\n✅ Match detection is working perfectly!")

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    bot.remove_webhook()
    print("✅ Bot Polling...")
    bot.infinity_polling()
