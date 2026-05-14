import os, threading, requests, telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from http.server import HTTPServer, BaseHTTPRequestHandler
from match_engine import set_bot, start_poll_thread, get_live_match_message, get_debug_info, get_schedule_message

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
PORT = int(os.environ.get("PORT", 10000))
bot = telebot.TeleBot(BOT_TOKEN)
alert_users = set()

def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🏏 Live IPL Match", callback_data="live"))
    markup.row(InlineKeyboardButton("📅 Today's Schedule", callback_data="schedule"))
    return markup

@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id
    alert_users.add(uid)
    # ReplyKeyboardRemove niche wala message box hide kar dega
    bot.send_message(message.chat.id, "🏏 *Thrill Alert Activated!*", 
                     parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    bot.send_message(message.chat.id, "Matches ki excitement miss nahi hogi. Niche buttons use karein:", 
                     reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: True)
def handle_query(call):
    alert_users.add(call.from_user.id)
    if call.data == "live": msg = get_live_match_message()
    else: msg = get_schedule_message()
    
    try: bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, 
                               parse_mode="Markdown", reply_markup=main_menu())
    except: bot.send_message(call.message.chat.id, msg, parse_mode="Markdown", reply_markup=main_menu())

# ... Health Check Handler ...
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"Alive")
    def log_message(self, format, *args): pass

if __name__ == "__main__":
    set_bot(bot, alert_users)
    threading.Thread(target=lambda: HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever(), daemon=True).start()
    start_poll_thread()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
