import os
import threading
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from http.server import HTTPServer, BaseHTTPRequestHandler

import database
import feedback_sheet
from match_engine import (
    set_bot,
    start_poll_thread,
    get_live_match_message,
    get_schedule_message,
    get_status_message
)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "")
PORT = int(os.environ.get("PORT", 10000))

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🏏 Live Score", callback_data="live"),
        InlineKeyboardButton("📅 Upcoming Matches", callback_data="schedule")
    )
    markup.row(
        InlineKeyboardButton("🔔 Subscribe Alerts", callback_data="subscribe"),
        InlineKeyboardButton("🔕 Stop Alerts", callback_data="unsubscribe")
    )
    markup.row(
        InlineKeyboardButton("ℹ️ About", callback_data="about")
    )
    return markup

def persistent_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Thrill Alert Menu 🟢"))
    return markup

def feedback_menu(match_id):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔥 Loved it", callback_data=f"fb_5_{match_id}"),
        InlineKeyboardButton("👍 Good", callback_data=f"fb_4_{match_id}"),
        InlineKeyboardButton("😐 Okay", callback_data=f"fb_3_{match_id}"),
        InlineKeyboardButton("👎 Bad", callback_data=f"fb_1_{match_id}")
    )
    return markup

@bot.message_handler(commands=["start"])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "User"
    database.add_user(user_id, username)
    
    welcome_text = (
        "🏏 *Welcome to Thrill Alert!*\n\n"
        "Main aapko cricket matches ke *sirf important moments* pe alert karunga — "
        "taaki aap busy time me bhi action miss na karein.\n\n"
        "✅ Toss alerts\n"
        "✅ Live thrill score (out of 10)\n"
        "✅ Win probability\n"
        "✅ Turning point notifications\n"
        "✅ Match result summary\n\n"
        "_Aap automatically subscribed ho. Niche menu se options choose karein._"
    )
    
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=persistent_menu())
    bot.send_message(message.chat.id, "👇 *Select an option:*", parse_mode="Markdown", reply_markup=main_menu())
    
    if ADMIN_USER_ID and str(user_id) != ADMIN_USER_ID:
        try:
            bot.send_message(int(ADMIN_USER_ID), f"🆕 New user joined: @{username} (ID: {user_id})")
        except:
            pass

@bot.message_handler(commands=["stop"])
def cmd_stop(message):
    database.remove_user(message.from_user.id)
    bot.send_message(message.chat.id, "🔕 Alerts band kar diye gaye.\n\nWaapas chalu karne ke liye /start dabao.")

@bot.message_handler(commands=["status"])
def cmd_status(message):
    if str(message.from_user.id) == ADMIN_USER_ID:
        bot.send_message(message.chat.id, get_status_message(), parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ Admin only command.")

@bot.message_handler(func=lambda m: m.text == "Thrill Alert Menu 🟢")
def menu_button(message):
    bot.send_message(message.chat.id, "👇 *Select an option:*", parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: c.data in ["live", "schedule", "subscribe", "unsubscribe", "about"])
def handle_main_callbacks(call):
    user_id = call.from_user.id
    username = call.from_user.username or call.from_user.first_name or "User"
    
    try:
        bot.answer_callback_query(call.id)
    except:
        pass
    
    if call.data == "live":
        msg = get_live_match_message()
    elif call.data == "schedule":
        msg = get_schedule_message()
    elif call.data == "subscribe":
        database.add_user(user_id, username)
        msg = "✅ *Alerts ON*\n\nAap subscribe ho gaye. Ab har match ka thrill alert milega."
    elif call.data == "unsubscribe":
        database.remove_user(user_id)
        msg = "🔕 *Alerts OFF*\n\nAap unsubscribe ho gaye. Waapas chalu karne ke liye Subscribe dabao."
    elif call.data == "about":
        msg = (
            "ℹ️ *About Thrill Alert*\n\n"
            "Ye bot aapko cricket ke *only thrilling moments* pe alert karta hai.\n\n"
            "🎯 Smart algorithm based\n"
            "📊 Real-time win probability\n"
            "🔥 Thrill score out of 10\n"
            "⚡ Turning point detection\n\n"
            "_Built with ❤️ for cricket fans._"
        )
    else:
        msg = "Option not found."
    
    try:
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
    except:
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: c.data.startswith("fb_"))
def handle_feedback(call):
    try:
        bot.answer_callback_query(call.id, "Thanks for feedback! 🙏")
    except:
        pass
    
    try:
        parts = call.data.split("_")
        rating = int(parts[1])
        match_id = parts[2] if len(parts) > 2 else "unknown"
        
        user_id = call.from_user.id
        username = call.from_user.username or call.from_user.first_name or "User"
        
        feedback_sheet.log_feedback(
            user_id, username, f"Match {match_id}", "N/A", rating, ""
        )
        
        bot.edit_message_text(
            "🙏 *Thanks for your feedback!*\n\nIs feedback se hum bot ko aur better banayenge.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"[Feedback Handler Error] {e}")

@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.send_message(
        message.chat.id,
        "👇 Niche menu button dabao ya /start type karo.",
        reply_markup=persistent_menu()
    )

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Thrill Alert Bot is Alive")
    def log_message(self, format, *args):
        pass

def start_health_server():
    HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever()

if __name__ == "__main__":
    print("=" * 50)
    print("🏏 THRILL ALERT BOT - Starting...")
    print("=" * 50)
    
    set_bot(bot)
    
    threading.Thread(target=start_health_server, daemon=True).start()
    print("[Main] Health server started.")
    
    start_poll_thread()
    print("[Main] Engine polling started.")
    
    print("[Main] Bot ready. Listening for messages...")
    bot.infinity_polling(skip_pending=True)
