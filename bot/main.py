import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import TeleBot, types
from match_engine import get_live_ipl_match

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = TeleBot(TOKEN)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), SimpleHandler).serve_forever()

@bot.message_handler(commands=["start"])
def start_cmd(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🏏 Live IPL Match")
    bot.send_message(message.chat.id, "🔍 <b>Scanner Bot Active!</b>\nTap the button to scan API data.", reply_markup=kb, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def live_match(message):
    result = get_live_ipl_match()
    
    # Agar match mil gaya
    if "match_id" in result:
        bot.send_message(message.chat.id, f"✅ <b>Match Found!</b>\n\n{result['team1']} vs {result['team2']}\nStatus: {result['status']}", parse_mode="HTML")
    else:
        # Agar nahi mila, toh API ki report dikhao
        series_list = "\n".join(result.get("found_series", ["None"]))
        bot.send_message(message.chat.id, f"❌ <b>Detection Report:</b>\n\n<b>Error:</b> {result['error']}\n\n<b>Top Series in API:</b>\n{series_list}", parse_mode="HTML")

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
