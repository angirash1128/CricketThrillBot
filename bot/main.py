# main.py
# Thrill Alert Bot - Main File

import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import telebot
from telebot import types

from database import (
    setup_database, user_exists, is_setup_complete,
    create_user, update_user_field, complete_setup,
    get_user, get_all_active_users,
    stop_notifications, resume_notifications, update_last_active
)
from feedback_sheet import setup_sheet_headers, save_feedback
from match_engine import get_live_ipl_match, get_match_scorecard, \
    parse_current_innings, detect_thrills


# ─────────────────────────────────────────
# WEB SERVER
# ─────────────────────────────────────────

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Thrill Alert Bot is running!")

    def log_message(self, format, *args):
        pass


def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()


# ─────────────────────────────────────────
# BOT SETUP
# ─────────────────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable nahi mili!")

bot = telebot.TeleBot(TOKEN, skip_pending=True)


# ─────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────

WHATSAPP_LINK = "https://whatsapp.com/channel/0029VbCxEWIKwqSaq8lHO517"

IPL_TEAMS = [
    "Mumbai Indians 🔵",
    "Chennai Super Kings 🟡",
    "Royal Challengers Bengaluru 🔴",
    "Kolkata Knight Riders 🟣",
    "Delhi Capitals 🔵",
    "Punjab Kings 🔴",
    "Rajasthan Royals 🩷",
    "Sunrisers Hyderabad 🟠",
    "Gujarat Titans 🔵",
    "Lucknow Super Giants 🩵"
]

ALERT_OPTIONS = [
    "Only My Team Matches",
    "All IPL Matches",
    "Big Matches Only (Playoffs, Finals, Super Overs)"
]


# ─────────────────────────────────────────
# STATE VARIABLES
# ─────────────────────────────────────────

sos_state = {}
current_match = {"match_id": None, "team1": None, "team2": None}
user_states = {}
feedback_temp = {}


# ─────────────────────────────────────────
# HELPER: BOTTOM MENU
# ─────────────────────────────────────────

def get_bottom_menu():
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        is_persistent=True
    )
    keyboard.row("🏏 Live IPL Match", "⭐ Give Feedback")
    keyboard.row("⚙️ Settings", "📢 Share Bot")
    keyboard.row("❓ Help")
    return keyboard


# ─────────────────────────────────────────
# HELPER: BROADCAST
# ─────────────────────────────────────────

def broadcast_message(text, reply_markup=None):
    users = get_all_active_users()

    for user in users:
        try:
            bot.send_message(
                user["user_id"],
                text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            time.sleep(0.05)
        except Exception as e:
            print(f"Broadcast failed {user['user_id']}: {e}")


# ─────────────────────────────────────────
# HELPER: SOS
# ─────────────────────────────────────────

def send_sos_alert(user_id, message_text):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            "✅ I am Watching",
            callback_data="sos_watching"
        )
    )

    try:
        bot.send_message(
            user_id,
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"SOS error {user_id}: {e}")


def start_sos_for_all(alert_message):
    users = get_all_active_users()

    for user in users:
        uid = user["user_id"]
        sos_state[uid] = {
            "message": alert_message,
            "count": 0,
            "active": True
        }

    def sos_loop():
        for _ in range(5):
            time.sleep(30)
            for uid in list(sos_state.keys()):
                state = sos_state.get(uid)
                if state and state["active"] and state["count"] < 5:
                    send_sos_alert(uid, state["message"])
                    sos_state[uid]["count"] += 1
                    if sos_state[uid]["count"] >= 5:
                        sos_state[uid]["active"] = False

    threading.Thread(target=sos_loop, daemon=True).start()


# ─────────────────────────────────────────
# /START
# ─────────────────────────────────────────

@bot.message_handler(commands=["start"])
def handle_start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "Cricket Fan"

    if user_exists(user_id):
        update_last_active(user_id)

    if user_exists(user_id) and is_setup_complete(user_id):
        bot.send_message(
            user_id,
            f"🏏 Welcome back, <b>{name}</b>!\n\n"
            f"IPL 2026 alerts are active. 🔔\n"
            f"I will notify you when something exciting happens!",
            reply_markup=get_bottom_menu(),
            parse_mode="HTML"
        )
        return

    create_user(user_id, name)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(
            "🔔 Set Up My Alerts",
            callback_data="setup_start"
        )
    )

    bot.send_message(
        user_id,
        f"🏏 <b>Welcome to Thrill Alert!</b>\n\n"
        f"Hi <b>{name}</b>! 👋\n\n"
        f"Never miss an exciting IPL 2026 moment again!\n\n"
        f"I will alert you about:\n"
        f"• 🚨 Wickets\n"
        f"• ⚡ Momentum shifts\n"
        f"• 🔴 Thriller finishes\n"
        f"• 🔥 Super Overs\n\n"
        f"Let's set up your alerts in 2 quick steps!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ─────────────────────────────────────────
# ONBOARDING
# ─────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "setup_start")
def setup_start(call):
    bot.answer_callback_query(call.id)

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(team, callback_data=f"team_{i}")
        for i, team in enumerate(IPL_TEAMS)
    ]
    keyboard.add(*buttons)

    bot.edit_message_text(
        "🏏 <b>Step 1 of 2: Choose Your Favourite Team</b>\n\n"
        "Which IPL team do you support? 👇",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("team_"))
def handle_team_selection(call):
    bot.answer_callback_query(call.id)

    user_id = call.from_user.id
    team_index = int(call.data.split("_")[1])
    selected_team = IPL_TEAMS[team_index]

    update_user_field(user_id, "favorite_team", selected_team)

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(
            "🏏 Only My Team Matches", callback_data="pref_0"
        ),
        types.InlineKeyboardButton(
            "🌐 All IPL Matches", callback_data="pref_1"
        ),
        types.InlineKeyboardButton(
            "🏆 Big Matches Only (Playoffs, Finals, Super Overs)",
            callback_data="pref_2"
        )
    )

    bot.edit_message_text(
        f"✅ Team saved: <b>{selected_team}</b>\n\n"
        f"🔔 <b>Step 2 of 2: Alert Preference</b>\n\n"
        f"Which matches do you want alerts for? 👇",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("pref_"))
def handle_alert_preference(call):
    bot.answer_callback_query(call.id)

    user_id = call.from_user.id
    pref_index = int(call.data.split("_")[1])
    selected_pref = ALERT_OPTIONS[pref_index]

    update_user_field(user_id, "alert_preference", selected_pref)
    complete_setup(user_id)

    user = get_user(user_id)
    team = user.get("favorite_team", "your team")

    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(
            "📱 Join WhatsApp Channel",
            url=WHATSAPP_LINK
        )
    )

    bot.edit_message_text(
        f"🎉 <b>Setup Complete!</b>\n\n"
        f"✅ Favourite Team: {team}\n"
        f"✅ Alert Preference: {selected_pref}\n\n"
        f"🔔 You are now subscribed to IPL 2026 alerts!\n\n"
        f"📱 Join our WhatsApp Channel for more updates:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    bot.send_message(
        user_id,
        "🏏 You are all set! Use the menu below to explore:",
        reply_markup=get_bottom_menu()
    )


# ─────────────────────────────────────────
# MAIN MENU
# ─────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "main_menu")
def handle_main_menu(call):
    user_id = call.from_user.id
    name = call.from_user.first_name or "Cricket Fan"

    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    try:
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )
    except Exception:
        pass

    bot.send_message(
        user_id,
        f"🏠 <b>Main Menu</b>\n\n"
        f"Hi <b>{name}</b>! Use the buttons below 👇",
        reply_markup=get_bottom_menu(),
        parse_mode="HTML"
    )


# ─────────────────────────────────────────
# LIVE MATCH
# ─────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def handle_live_match(message):
    user_id = message.from_user.id
    update_last_active(user_id)

    match = get_live_ipl_match()

    if not match:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton(
                "⭐ Give Feedback", callback_data="feedback_start"
            ),
            types.InlineKeyboardButton(
                "⚙️ Settings", callback_data="settings"
            )
        )
        keyboard.row(
            types.InlineKeyboardButton(
                "🏠 Main Menu", callback_data="main_menu"
            )
        )

        bot.send_message(
            user_id,
            "🏏 <b>No live IPL match right now.</b>\n\n"
            "I will alert you when a match starts! 🔔",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(
            "🔔 Get Alerts for This Match",
            callback_data=f"subscribe_{match['match_id']}"
        )
    )
    keyboard.row(
        types.InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
        types.InlineKeyboardButton("⭐ Give Feedback", callback_data="feedback_start")
    )
    keyboard.row(
        types.InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
    )

    bot.send_message(
        user_id,
        f"🏏 <b>Live IPL Match</b>\n\n"
        f"<b>{match['team1']}</b> vs <b>{match['team2']}</b>\n\n"
        f"📊 Status: {match['status']}\n"
        f"⚡ State: {match['state']}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("subscribe_"))
def handle_subscribe_match(call):
    bot.answer_callback_query(call.id, "✅ Alerts activated!", show_alert=False)

    user_id = call.from_user.id
    match_id = call.data.split("_")[1]

    update_user_field(user_id, "selected_match_id", match_id)

    bot.send_message(
        user_id,
        "🔔 <b>Alerts Activated!</b>\n\n"
        "I will notify you about every exciting moment. 🏏",
        reply_markup=get_bottom_menu(),
        parse_mode="HTML"
    )


# ─────────────────────────────────────────
# FEEDBACK
# ─────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "⭐ Give Feedback")
def handle_feedback_button(message):
    start_feedback(message.from_user.id, message.chat.id)


@bot.callback_query_handler(func=lambda c: c.data == "feedback_start")
def handle_feedback_callback(call):
    bot.answer_callback_query(call.id)
    start_feedback(call.from_user.id, call.message.chat.id)


def start_feedback(user_id, chat_id):
    feedback_temp[user_id] = {"step": "rating", "rating": None}

    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("1 ⭐", callback_data="rate_1"),
        types.InlineKeyboardButton("2 ⭐", callback_data="rate_2"),
        types.InlineKeyboardButton("3 ⭐", callback_data="rate_3"),
        types.InlineKeyboardButton("4 ⭐", callback_data="rate_4"),
        types.InlineKeyboardButton("5 ⭐", callback_data="rate_5")
    )

    bot.send_message(
        chat_id,
        "💬 <b>Share Your Feedback</b>\n\n"
        "We are currently in the development stage.\n"
        "If you notice any issue, missing feature, or\n"
        "have any suggestion, please share it with us.\n\n"
        "Your feedback directly helps us improve\n"
        "<b>Thrill Alert</b>. Thank you! 🙏\n\n"
        "⭐ First, how would you rate this bot?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("rate_"))
def handle_rating(call):
    bot.answer_callback_query(call.id)

    user_id = call.from_user.id
    rating = int(call.data.split("_")[1])

    feedback_temp[user_id] = {"rating": rating, "step": "text"}
    user_states[user_id] = "awaiting_feedback_text"

    bot.edit_message_text(
        f"You rated: {'⭐' * rating}\n\n"
        f"📝 Now please type your feedback or suggestion:",
        call.message.chat.id,
        call.message.message_id
    )


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_feedback_text")
def handle_feedback_text(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "User"
    rating = feedback_temp.get(user_id, {}).get("rating", 5)

    saved = save_feedback(user_id, name, rating, message.text)

    user_states.pop(user_id, None)
    feedback_temp.pop(user_id, None)

    response = (
        "✅ <b>Thank you for your feedback!</b>\n\n"
        "Your response has been saved. 🙏"
        if saved else
        "✅ <b>Thank you for your feedback!</b>\n\n"
        "We noted your response."
    )

    bot.send_message(
        user_id,
        response,
        reply_markup=get_bottom_menu(),
        parse_mode="HTML"
    )


# ─────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "⚙️ Settings")
def handle_settings_button(message):
    show_settings(message.from_user.id, message.chat.id)


@bot.callback_query_handler(func=lambda c: c.data == "settings")
def handle_settings_callback(call):
    bot.answer_callback_query(call.id)
    show_settings(call.from_user.id, call.message.chat.id)


def show_settings(user_id, chat_id):
    user = get_user(user_id)

    if not user:
        bot.send_message(chat_id, "Please use /start first.")
        return

    team = user.get("favorite_team") or "Not set"
    pref = user.get("alert_preference") or "Not set"
    notif_on = user.get("notifications_enabled") == 1
    notif_status = "🔔 On" if notif_on else "🔕 Off"
    notif_btn = "🔕 Stop Alerts" if notif_on else "🔔 Resume Alerts"
    notif_cb = "stop_alerts" if notif_on else "resume_alerts"

    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(
            "🏏 Change Favourite Team", callback_data="change_team"
        )
    )
    keyboard.row(
        types.InlineKeyboardButton(
            "🔔 Change Alert Preference", callback_data="change_pref"
        )
    )
    keyboard.row(
        types.InlineKeyboardButton(notif_btn, callback_data=notif_cb)
    )
    keyboard.row(
        types.InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
    )

    bot.send_message(
        chat_id,
        f"⚙️ <b>Your Settings</b>\n\n"
        f"🏏 Favourite Team: <b>{team}</b>\n"
        f"🔔 Alert Preference: <b>{pref}</b>\n"
        f"📳 Notifications: <b>{notif_status}</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda c: c.data == "change_team")
def change_team(call):
    bot.answer_callback_query(call.id)

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(team, callback_data=f"newteam_{i}")
        for i, team in enumerate(IPL_TEAMS)
    ]
    keyboard.add(*buttons)

    bot.send_message(
        call.message.chat.id,
        "🏏 <b>Choose Your New Favourite Team:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("newteam_"))
def handle_new_team(call):
    bot.answer_callback_query(call.id)

    user_id = call.from_user.id
    selected_team = IPL_TEAMS[int(call.data.split("_")[1])]

    update_user_field(user_id, "favorite_team", selected_team)

    bot.send_message(
        call.message.chat.id,
        f"✅ Favourite team updated: <b>{selected_team}</b>",
        reply_markup=get_bottom_menu(),
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda c: c.data == "change_pref")
def change_pref(call):
    bot.answer_callback_query(call.id)

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(
            "🏏 Only My Team Matches", callback_data="newpref_0"
        ),
        types.InlineKeyboardButton(
            "🌐 All IPL Matches", callback_data="newpref_1"
        ),
        types.InlineKeyboardButton(
            "🏆 Big Matches Only", callback_data="newpref_2"
        )
    )

    bot.send_message(
        call.message.chat.id,
        "🔔 <b>Choose Alert Preference:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("newpref_"))
def handle_new_pref(call):
    bot.answer_callback_query(call.id)

    user_id = call.from_user.id
    selected_pref = ALERT_OPTIONS[int(call.data.split("_")[1])]

    update_user_field(user_id, "alert_preference", selected_pref)

    bot.send_message(
        call.message.chat.id,
        f"✅ Alert preference updated: <b>{selected_pref}</b>",
        reply_markup=get_bottom_menu(),
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda c: c.data == "stop_alerts")
def handle_stop_alerts(call):
    bot.answer_callback_query(call.id)

    stop_notifications(call.from_user.id)

    bot.send_message(
        call.message.chat.id,
        "🔕 <b>Alerts Stopped</b>\n\n"
        "Tap Settings → Resume Alerts to turn on again.",
        reply_markup=get_bottom_menu(),
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda c: c.data == "resume_alerts")
def handle_resume_alerts(call):
    bot.answer_callback_query(call.id)

    resume_notifications(call.from_user.id)

    bot.send_message(
        call.message.chat.id,
        "🔔 <b>Alerts Resumed!</b>\n\n"
        "You will now get IPL 2026 alerts. 🏏",
        reply_markup=get_bottom_menu(),
        parse_mode="HTML"
    )


# ─────────────────────────────────────────
# SOS WATCHING
# ─────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "sos_watching")
def handle_sos_watching(call):
    user_id = call.from_user.id

    if user_id in sos_state:
        sos_state[user_id]["active"] = False

    bot.answer_callback_query(call.id, "✅ Enjoy the match! 🏏")

    bot.send_message(
        user_id,
        "🏏 <b>Enjoy the match!</b>\n\n"
        "I will keep alerting you about exciting moments.",
        reply_markup=get_bottom_menu(),
        parse_mode="HTML"
    )


# ─────────────────────────────────────────
# SHARE BOT
# ─────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "📢 Share Bot")
def handle_share(message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(
            "📱 Join WhatsApp Channel",
            url=WHATSAPP_LINK
        )
    )
    keyboard.row(
        types.InlineKeyboardButton(
            "📤 Share on Telegram",
            url="https://t.me/share/url?url=https://t.me/Cricket_Thrill_Alert_Bot&text=Get%20live%20IPL%202026%20alerts!"
        )
    )

    bot.send_message(
        message.from_user.id,
        "📢 <b>Share Thrill Alert!</b>\n\n"
        "🏏 Get exciting IPL 2026 alerts on Telegram!\n\n"
        "• 🚨 Wicket Alerts\n"
        "• ⚡ Momentum Shifts\n"
        "• 🔴 Thriller Finishes\n"
        "• 🔥 Super Over Alerts\n\n"
        "👉 @Cricket_Thrill_Alert_Bot\n\n"
        f"📱 WhatsApp: {WHATSAPP_LINK}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ─────────────────────────────────────────
# HELP
# ─────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "❓ Help")
def handle_help(message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
        types.InlineKeyboardButton("⚙️ Settings", callback_data="settings")
    )

    bot.send_message(
        message.from_user.id,
        "❓ <b>How to Use Thrill Alert</b>\n\n"
        "• Tap <b>🏏 Live IPL Match</b> to check current game.\n"
        "• Tap <b>⚙️ Settings</b> to manage preferences.\n"
        "• Tap <b>📢 Share Bot</b> to invite friends.\n"
        "• Tap <b>⭐ Give Feedback</b> to help us improve.\n\n"
        "🔔 <b>Commands:</b>\n"
        "• /stop — Stop all alerts\n"
        "• /resume — Resume alerts\n\n"
        "Everything works through buttons! 🏏",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ─────────────────────────────────────────
# /STOP /RESUME
# ─────────────────────────────────────────

@bot.message_handler(commands=["stop"])
def handle_stop_command(message):
    stop_notifications(message.from_user.id)

    bot.send_message(
        message.from_user.id,
        "🔕 Alerts stopped. Send /resume to turn on again.",
        reply_markup=get_bottom_menu()
    )


@bot.message_handler(commands=["resume"])
def handle_resume_command(message):
    resume_notifications(message.from_user.id)

    bot.send_message(
        message.from_user.id,
        "🔔 Alerts resumed! You will now get IPL 2026 alerts. 🏏",
        reply_markup=get_bottom_menu()
    )


# ─────────────────────────────────────────
# MATCH POLLING LOOP
# ─────────────────────────────────────────

def match_poll_loop():
    print("Match polling loop started")

    while True:
        try:
            match = get_live_ipl_match()

            if not match:
                time.sleep(60)
                continue

            match_id = match["match_id"]

            if current_match["match_id"] != match_id:
                current_match["match_id"] = match_id
                current_match["team1"] = match["team1"]
                current_match["team2"] = match["team2"]

                print(f"New match: {match['team1']} vs {match['team2']}")

                broadcast_message(
                    f"🏏 <b>Match Alert!</b>\n\n"
                    f"<b>{match['team1']}</b> vs <b>{match['team2']}</b>\n"
                    f"IPL 2026 is now being monitored.\n\n"
                    f"I will alert you when something EXCITING happens!\n"
                    f"Tap 🏏 Live IPL Match to see the score."
                )

            scorecard = get_match_scorecard(match_id)
            innings_data = parse_current_innings(scorecard)

            if innings_data:
                alerts = detect_thrills(match_id, innings_data)

                for alert in alerts:
                    print(f"Thrill: {alert['type']}")

                    if alert["is_mega"]:
                        start_sos_for_all(alert["message"])
                    else:
                        broadcast_message(alert["message"])

        except Exception as e:
            print(f"Poll error: {e}")

        time.sleep(60)


# ─────────────────────────────────────────
# START
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("Thrill Alert Bot starting...")

    threading.Thread(target=run_web_server, daemon=True).start()
    print("Web server started")

    setup_database()
    setup_sheet_headers()

    threading.Thread(target=match_poll_loop, daemon=True).start()

    print("Bot is running!")

    bot.infinity_polling(timeout=60, long_polling_timeout=60)
