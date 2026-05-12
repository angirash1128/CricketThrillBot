import os
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from ipl_schedule import format_schedule_message, get_today_matches, format_time_12h
from match_engine import set_bot, start_poll_thread, get_live_match_message, get_debug_info

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
    
    today_matches = get_today_matches()
    if today_matches:
        match_info = "\n".join([
            f"🏏 *{m[5]} vs {m[6]}*\n   ⏰ {format_time_12h(m[3], m[4])} IST | 📍 {m[7]}"
            for m in today_matches
        ])
    else:
        match_info = "No IPL match today 😴"
    
    msg = f"🏏 *Welcome to Thrill Alert!*\n\nYour IPL excitement detector 🚨\n\n*Today:*\n{match_info}\n\nUse buttons below 👇"
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
    try:
        bot.edit_message_text(get_live_match_message(), call.message.chat.id, 
                            call.message.message_id, parse_mode="Markdown", reply_markup=main_menu())
    except:
        bot.send_message(call.message.chat.id, get_live_match_message(), 
                        parse_mode="Markdown", reply_markup=main_menu())


@bot.callback_query_handler(func=lambda c: c.data == "schedule")
def schedule(call):
    alert_users.add(call.from_user.id)
    try:
        bot.edit_message_text(format_schedule_message(), call.message.chat.id, 
                            call.message.message_id, parse_mode="Markdown", reply_markup=main_menu())
    except:
        bot.send_message(call.message.chat.id, format_schedule_message(), 
                        parse_mode="Markdown", reply_markup=main_menu())


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Thrill Alert is alive!")
    
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    
    def do_POST(self):
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
    
    start_poll_thread()
    print("[Poll] Thread started")
    
    bot.polling(none_stop=True, interval=0, timeout=25)
