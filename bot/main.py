import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import TeleBot, types
from match_engine import get_live_ipl_match

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = TeleBot(TOKEN)

# Simple Server for Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), SimpleHandler).serve_forever()

# MENU
def get_main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🏏 Live IPL Match")
    return kb

@bot.message_handler(commands=["start"])
def start_cmd(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔔 Set Up Alerts", callback_data="setup_now"))
    bot.send_message(message.chat.id, "🏏 <b>Thrill Alert Active!</b>\n\nClick below to start setup.", reply_markup=kb, parse_mode="HTML")

@bot.callback_query_handler(func=lambda c: c.data == "setup_now")
def setup_now(call):
    bot.answer_callback_query(call.id)
    # Simple reset - onboarding baad mein badhayenge, pehle start karwate hain
    bot.send_message(call.message.chat.id, "✅ <b>Setup Complete!</b>\n\nYou will get alerts for IPL matches.", reply_markup=get_main_menu(), parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def live_match(message):
    match = get_live_ipl_match()
    if not match:
        bot.send_message(message.chat.id, "❌ No live IPL match found right now.")
        return
    bot.send_message(message.chat.id, f"🏏 <b>{match['team1']}</b> vs <b>{match['team2']}</b>\nStatus: {match['status']}", parse_mode="HTML")

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    bot.remove_webhook()
    print("🚀 Polling...")
    bot.infinity_polling(skip_pending=True)
