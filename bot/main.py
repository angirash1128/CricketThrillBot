import os
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Updated imports to match the new Auto-Fetch Engine
from match_engine import set_bot, start_poll_thread, get_live_match_message, get_debug_info, get_schedule_message

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
PORT = int(os.environ.get("PORT", 10000))

bot = telebot.TeleBot(BOT_TOKEN)
alert_users = set()

def clear_webhook():
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true"
        requests.get(url, timeout=10)
        print("[Startup] Webhook cleared")
    except:
        pass

def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🏏 Live IPL Match", callback_data="live"))
    markup.row(InlineKeyboardButton("📅 Today's Schedule", callback_data="schedule"))
    return markup

@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id
    alert_users.add(uid)
    
    msg = (
        "🏏 *Welcome to Thrill Alert!*\n\n"
        "Your professional IPL excitement detector 🚨\n\n"
        "Ab sab kuch automated hai! Niche diye gaye buttons se "
        "real-time data check karein. 👇"
    )
    bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=main_menu())

@bot.message_handler(commands=["debug"])
def debug(message):
    alert_users.add(message.from_user.id)
    bot.send_message(message.chat.id, get_debug_info(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def any_msg(message):
    alert_users.add(message.from_user.id)
    bot.send_message(message.chat.id, "Use /start 👋", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: c.data == "live")
def live(call):
    alert_users.add(call.from_user.id)
    msg_text = get_live_match_message()
    try:
        bot.edit_message_text(msg_text, call.message.chat.id, 
                              call.message.message_id, parse_mode="Markdown", reply_markup=main_menu())
    except:
        bot.send_message(call.message.chat.id, msg_text, 
                         parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: c.data == "schedule")
def schedule(call):
    alert_users.add(call.from_user.id)
    msg_text = get_schedule_message()
    try:
        bot.edit_message_text(msg_text, call.message.chat.id, 
                              call.message.message_id, parse_mode="Markdown", reply_markup=main_menu())
    except:
        bot.send_message(call.message.chat.id, msg_text, 
                         parse_mode="Markdown", reply_markup=main_menu())

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Thrill Alert is alive!")
    
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        pass

def start_http():
    HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever()

if __name__ == "__main__":
    clear_webhook()
    set_bot(bot, alert_users)
    
    threading.Thread(target=start_http, daemon=True).start()
    print(f"[HTTP] Server on port {PORT}")
    
    # Starting the automated engine
    start_poll_thread()
    print("[Engine] Automated background thread started")
    
    bot.polling(none_stop=True, interval=0, timeout=25)
