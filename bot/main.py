import os, threading, telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from http.server import HTTPServer, BaseHTTPRequestHandler
from match_engine import set_bot, start_poll_thread, get_live_match_message, get_schedule_message

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
PORT = int(os.environ.get("PORT", 10000))
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
alert_users = set()

def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🏏 Live Score", callback_data="live"), 
               InlineKeyboardButton("📅 Full Schedule", callback_data="schedule"))
    return markup

def hide_keyboard():
    # Ye niche ke area ko minimize rakhega
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.add(KeyboardButton("Menu Activated 🔓"))
    return markup

@bot.message_handler(commands=["start"])
def start(message):
    alert_users.add(message.from_user.id)
    # Buttons send karke keyboard ko clean rakhenge
    bot.send_message(message.chat.id, "🏏 *Thrill Alert Activated!*", 
                     parse_mode="Markdown", reply_markup=hide_keyboard())
    bot.send_message(message.chat.id, "Main aapko Toss aur Result ke alerts bhejta rahoonga. Niche buttons use karein:", 
                     reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: True)
def handle_query(call):
    alert_users.add(call.from_user.id)
    msg = get_live_match_message() if call.data == "live" else get_schedule_message()
    try:
        bot.answer_callback_query(call.id)
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, 
                               parse_mode="Markdown", reply_markup=main_menu())
    except:
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown", reply_markup=main_menu())

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"Alive")
    def log_message(self, format, *args): pass

if __name__ == "__main__":
    set_bot(bot, alert_users)
    threading.Thread(target=lambda: HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever(), daemon=True).start()
    start_poll_thread()
    bot.infinity_polling(skip_pending=True)
