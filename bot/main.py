# main.py
# Cricket Thrill Alert Bot - Main File
# Ye file bot ka poora logic handle karti hai

import os
import time
import threading
from datetime import datetime

import telebot
from telebot import types

# Apni files import karo
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
# BOT SETUP
# ─────────────────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN environment variable nahi mili!")

bot = telebot.TeleBot(TOKEN)

# ─────────────────────────────────────────
# IPL TEAMS
# ─────────────────────────────────────────

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

# Alert preference options
ALERT_OPTIONS = [
    "Only My Team Matches",
    "All IPL Matches",
    "Big Matches Only (Playoffs, Finals, Super Overs)"
]

# ─────────────────────────────────────────
# SOS (MEGA ALERT) STATE
# Tracks which users are in SOS mode
# Format: { user_id: { "message": ..., "count": ..., "active": ... } }
# ─────────────────────────────────────────
sos_state = {}

# ─────────────────────────────────────────
# CURRENT MATCH STATE
# ─────────────────────────────────────────
current_match = {
    "match_id": None,
    "team1": None,
    "team2": None,
    "state": None
}

# User onboarding state tracking
# Format: { user_id: "step_name" }
user_states = {}

# Temporary feedback storage while collecting
# Format: { user_id: { "rating": ..., "step": ... } }
feedback_temp = {}

# ─────────────────────────────────────────
# HELPER: BOTTOM MENU KEYBOARD
# ─────────────────────────────────────────

def get_bottom_menu():
    """
    Bottom pe dikhne wala persistent keyboard banao
    Har important message ke baad yahi dikhega
    """
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        persistent=True
    )
    keyboard.row("🏏 Live IPL Match", "⭐ Give Feedback")
    keyboard.row("⚙️ Settings", "📢 Share Bot")
    keyboard.row("❓ Help")
    return keyboard

def get_main_menu_inline():
    """Main menu ke liye inline buttons"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("⭐ Give Feedback", callback_data="feedback_start"),
        types.InlineKeyboardButton("⚙️ Settings", callback_data="settings")
    )
    keyboard.row(
        types.InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
    )
    return keyboard

# ─────────────────────────────────────────
# HELPER: SEND TO ALL USERS (BROADCAST)
# ─────────────────────────────────────────

def broadcast_message(text, reply_markup=None):
    """
    Saare active users ko message bhejo
    Ek user fail ho to baaki ko bhejte raho
    """
    users = get_all_active_users()
    success = 0
    failed = 0
    
    for user in users:
        try:
            bot.send_message(
                user["user_id"],
                text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            success += 1
            time.sleep(0.05)  # Rate limiting ke liye thoda wait
        except Exception as e:
            failed += 1
            # Log karo but continue karo
            print(f"❌ Broadcast failed for {user['user_id']}: {e}")
    
    return success, failed

# ─────────────────────────────────────────
# HELPER: SEND MEGA ALERT (SOS MODE)
# ─────────────────────────────────────────

def send_sos_alert(user_id, message_text):
    """
    SOS alert ek user ko bhejo
    Inline button: ✅ I am Watching
    """
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
        print(f"❌ SOS send error for {user_id}: {e}")

def start_sos_for_all(alert_message):
    """
    Saare active users ke liye SOS mode start karo
    30 second intervals, max 5 baar
    """
    users = get_all_active_users()
    
    for user in users:
        uid = user["user_id"]
        sos_state[uid] = {
            "message": alert_message,
            "count": 0,
            "active": True
        }
    
    # SOS thread start karo
    def sos_loop():
        for attempt in range(5):
            time.sleep(30)
            
            users_to_alert = list(sos_state.keys())
            
            for uid in users_to_alert:
                state = sos_state.get(uid)
                if state and state["active"] and state["count"] < 5:
                    send_sos_alert(uid, state["message"])
                    sos_state[uid]["count"] += 1
                    
                    # 5 baar ho gaya to band karo
                    if sos_state[uid]["count"] >= 5:
                        sos_state[uid]["active"] = False
    
    thread = threading.Thread(target=sos_loop, daemon=True)
    thread.start()

# ─────────────────────────────────────────
# /START COMMAND
# ─────────────────────────────────────────

@bot.message_handler(commands=["start"])
def handle_start(message):
    """
    /start command handle karo
    New user: onboarding flow
    Returning user: welcome back
    """
    user_id = message.from_user.id
    name = message.from_user.first_name or "Cricket Fan"
    
    update_last_active(user_id)
    
    # Returning user check
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
    
    # New user - create in database
    create_user(user_id, name)
    
    # Step 1: Welcome message
    user_states[user_id] = "awaiting_notification_pref"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(
            "🔔 Set Up My Alerts", 
            callback_data="setup_start"
        )
    )
    
    bot.send_message(
        user_id,
        f"🏏 <b>Welcome to Cricket Thrill Alert!</b>\n\n"
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
# ONBOARDING: SETUP START
# ─────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "setup_start")
def setup_start(call):
    """Onboarding step 1: Favorite team chunao"""
    user_id = call.from_user.id
    
    # Team selection keyboard banao
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
    """User ne team chunni - save karo aur alert preference pucho"""
    user_id = call.from_user.id
    
    # Team index nikalo
    team_index = int(call.data.split("_")[1])
    selected_team = IPL_TEAMS[team_index]
    
    # Database mein save karo
    update_user_field(user_id, "favorite_team", selected_team)
    
    # Alert preference keyboard
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(
            "🏏 Only My Team Matches", 
            callback_data="pref_0"
        ),
        types.InlineKeyboardButton(
            "🌐 All IPL Matches", 
            callback_data="pref_1"
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
    """User ne alert preference chuna - setup complete karo"""
    user_id = call.from_user.id
    
    pref_index = int(call.data.split("_")[1])
    selected_pref = ALERT_OPTIONS[pref_index]
    
    # Database mein save karo
    update_user_field(user_id, "alert_preference", selected_pref)
    complete_setup(user_id)
    
    # WhatsApp channel inline button
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(
            "📱 Join WhatsApp Channel", 
            url="https://whatsapp.com/channel/YOUR_CHANNEL_LINK"
        )
    )
    keyboard.row(
        types.InlineKeyboardButton(
            "🏠 Go to Main Menu", 
            callback_data="main_menu"
        )
    )
    
    user = get_user(user_id)
    team = user.get("favorite_team", "your team")
    
    bot.edit_message_text(
        f"🎉 <b>Setup Complete!</b>\n\n"
        f"✅ Favourite Team: {team}\n"
        f"✅ Alert Preference: {selected_pref}\n\n"
        f"🔔 You are now subscribed to IPL 2026 alerts!\n\n"
        f"📱 Join our WhatsApp Channel for more cricket updates:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    # Bottom menu dikhao
    bot.send_message(
        user_id,
        "🏏 Use the menu below to get started!",
        reply_markup=get_bottom_menu()
    )

# ─────────────────────────────────────────
# MAIN MENU CALLBACK
# ─────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "main_menu")
def handle_main_menu(call):
    """Main menu dikhao"""
    user_id = call.from_user.id
    name = call.from_user.first_name or "Cricket Fan"
    
    bot.send_message(
        user_id,
        f"🏠 <b>Main Menu</b>\n\nHi {name}! What would you like to do?",
        reply_markup=get_bottom_menu(),
        parse_mode="HTML"
    )

# ─────────────────────────────────────────
# LIVE MATCH BUTTON
# ─────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def handle_live_match(message):
    """Live IPL match card dikhao"""
    user_id = message.from_user.id
    update_last_active(user_id)
    
    # API se live match lo
    match = get_live_ipl_match()
    
    if not match:
        # Koi live match nahi
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton("⭐ Give Feedback", callback_data="feedback_start"),
            types.InlineKeyboardButton("⚙️ Settings", callback_data="settings")
        )
        keyboard.row(
            types.InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        )
        
        bot.send_message(
            user_id,
            "🏏 <b>No live IPL match right now.</b>\n\n"
            "I will automatically alert you when a match starts!\n"
            "Make sure your notifications are enabled. 🔔",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    
    # Match card dikhao
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
    """User ne match ke liye alerts subscribe kiya"""
    user_id = call.from_user.id
    match_id = call.data.split("_")[1]
    
    update_user_field(user_id, "selected_match_id", match_id)
    
    bot.answer_callback_query(
        call.id, 
        "✅ You will get alerts for this match!", 
        show_alert=False
    )
    
    bot.send_message(
        user_id,
        "🔔 <b>Alerts Activated!</b>\n\n"
        "I will notify you about every exciting moment in this match.\n"
        "Sit back and enjoy! 🏏",
        reply_markup=get_bottom_menu(),
        parse_mode="HTML"
    )

# ─────────────────────────────────────────
# FEEDBACK SYSTEM
# ─────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "⭐ Give Feedback")
def handle_feedback_button(message):
    """Feedback button tap kiya"""
    start_feedback(message.from_user.id, message.chat.id)

@bot.callback_query_handler(func=lambda c: c.data == "feedback_start")
def handle_feedback_callback(call):
    """Feedback inline button tap kiya"""
    start_feedback(call.from_user.id, call.message.chat.id)

def start_feedback(user_id, chat_id):
    """Feedback flow start karo"""
    feedback_temp[user_id] = {"step": "rating", "rating": None}
    
    # Rating keyboard
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
        "<b>Cricket Thrill Alert</b>. Thank you! 🙏\n\n"
        "⭐ First, how would you rate this bot?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("rate_"))
def handle_rating(call):
    """User ne rating di"""
    user_id = call.from_user.id
    rating = int(call.data.split("_")[1])
    
    if user_id in feedback_temp:
        feedback_temp[user_id]["rating"] = rating
        feedback_temp[user_id]["step"] = "text"
    else:
        feedback_temp[user_id] = {"rating": rating, "step": "text"}
    
    bot.edit_message_text(
        f"You rated: {'⭐' * rating}\n\n"
        f"📝 Now please type your feedback or suggestion:\n"
        f"(Any issue, feature request, or comment)",
        call.message.chat.id,
        call.message.message_id
    )
    
    # User state set karo
    user_states[user_id] = "awaiting_feedback_text"

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_feedback_text")
def handle_feedback_text(message):
    """User ne feedback text likha - save karo"""
    user_id = message.from_user.id
    name = message.from_user.first_name or "User"
    feedback_text = message.text
    
    # Feedback temp se rating lo
    rating = feedback_temp.get(user_id, {}).get("rating", 5)
    
    # Google Sheets mein save karo
    saved = save_feedback(user_id, name, rating, feedback_text)
    
    # State clear karo
    user_states.pop(user_id, None)
    feedback_temp.pop(user_id, None)
    
    if saved:
        response = (
            "✅ <b>Thank you for your feedback!</b>\n\n"
            "Your response has been saved.\n"
            "We will work on making the bot better! 🏏"
        )
    else:
        response = (
            "✅ <b>Thank you for your feedback!</b>\n\n"
            "We noted your response.\n"
            "(Note: Sheet sync pending)"
        )
    
    bot.send_message(
        user_id,
        response,
        reply_markup=get_bottom_menu(),
        parse_mode="HTML"
    )

# ─────────────────────────────────────────
# SETTINGS MENU
# ─────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "⚙️ Settings")
def handle_settings_button(message):
    """Settings button tap kiya"""
    show_settings(message.from_user.id, message.chat.id)

@bot.callback_query_handler(func=lambda c: c.data == "settings")
def handle_settings_callback(call):
    """Settings inline button tap kiya"""
    show_settings(call.from_user.id, call.message.chat.id)

def show_settings(user_id, chat_id):
    """Settings menu dikhao"""
    user = get_user(user_id)
    
    if not user:
        bot.send_message(chat_id, "Please use /start first.")
        return
    
    team = user.get("favorite_team") or "Not set"
    pref = user.get("alert_preference") or "Not set"
    notif_status = "🔔 On" if user.get("notifications_enabled") == 1 else "🔕 Off"
    notif_btn_text = "🔕 Stop Alerts" if user.get("notifications_enabled") == 1 else "🔔 Resume Alerts"
    notif_callback = "stop_alerts" if user.get("notifications_enabled") == 1 else "resume_alerts"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("🏏 Change Favourite Team", callback_data="change_team")
    )
    keyboard.row(
        types.InlineKeyboardButton("🔔 Change Alert Preference", callback_data="change_pref")
    )
    keyboard.row(
        types.InlineKeyboardButton(notif_btn_text, callback_data=notif_callback)
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
    """Team change karo"""
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
    """New team save karo"""
    user_id = call.from_user.id
    team_index = int(call.data.split("_")[1])
    selected_team = IPL_TEAMS[team_index]
    
    update_user_field(user_id, "favorite_team", selected_team)
    
    bot.send_message(
        call.message.chat.id,
        f"✅ Favourite team updated to: <b>{selected_team}</b>",
        reply_markup=get_bottom_menu(),
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda c: c.data == "change_pref")
def change_pref(call):
    """Alert preference change karo"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🏏 Only My Team Matches", callback_data="newpref_0"),
        types.InlineKeyboardButton("🌐 All IPL Matches", callback_data="newpref_1"),
        types.InlineKeyboardButton("🏆 Big Matches Only", callback_data="newpref_2")
    )
    
    bot.send_message(
        call.message.chat.id,
        "🔔 <b>Choose Alert Preference:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("newpref_"))
def handle_new_pref(call):
    """New preference save karo"""
    user_id = call.from_user.id
    pref_index = int(call.data.split("_")[1])
    selected_pref = ALERT_OPTIONS[pref_index]
    
    update_user_field(user_id, "alert_preference", selected_pref)
    
    bot.send_message(
        call.message.chat.id,
        f"✅ Alert preference updated to: <b>{selected_pref}</b>",
        reply_markup=get_bottom_menu(),
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda c: c.data == "stop_alerts")
def handle_stop_alerts(call):
    """Alerts band karo"""
    stop_notifications(call.from_user.id)
    bot.send_message(
        call.message.chat.id,
        "🔕 <b>Alerts Stopped</b>\n\n"
        "You will not receive any alerts.\n"
        "Tap Settings → Resume Alerts to turn on again.",
        reply_markup=get_bottom_menu(),
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda c: c.data == "resume_alerts")
def handle_resume_alerts(call):
    """Alerts resume karo"""
    resume_notifications(call.from_user.id)
    bot.send_message(
        call.message.chat.id,
        "🔔 <b>Alerts Resumed!</b>\n\n"
        "You will now receive IPL 2026 alerts again. 🏏",
        reply_markup=get_bottom_menu(),
        parse_mode="HTML"
    )

# ─────────────────────────────────────────
# SOS: I AM WATCHING
# ─────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "sos_watching")
def handle_sos_watching(call):
    """User ne 'I am Watching' dabaya - SOS band karo"""
    user_id = call.from_user.id
    
    if user_id in sos_state:
        sos_state[user_id]["active"] = False
    
    bot.answer_callback_query(
        call.id,
        "✅ Great! Enjoy the match! 🏏",
        show_alert=False
    )
    
    bot.send_message(
        user_id,
        "🏏 <b>Enjoy the match!</b>\n\nI will keep alerting you about exciting moments.",
        reply_markup=get_bottom_menu(),
        parse_mode="HTML"
    )

# ─────────────────────────────────────────
# SHARE BOT
# ─────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "📢 Share Bot")
def handle_share(message):
    """Share bot message bhejo"""
    user_id = message.from_user.id
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(
            "📱 Join WhatsApp Channel",
            url="https://whatsapp.com/channel/YOUR_CHANNEL_LINK"
        )
    )
    keyboard.row(
        types.InlineKeyboardButton(
            "📤 Share on Telegram",
            url="https://t.me/share/url?url=https://t.me/Cricket_Thrill_Alert_Bot&text=Get%20live%20IPL%202026%20alerts%20on%20Telegram!"
        )
    )
    
    bot.send_message(
        user_id,
        "📢 <b>Share Cricket Thrill Alert!</b>\n\n"
        "🏏 Get exciting IPL 2026 alerts directly on Telegram!\n\n"
        "• 🚨 Wicket Alerts\n"
        "• ⚡ Momentum Shifts\n"
        "• 🔴 Thriller Finishes\n"
        "• 🔥 Super Over Alerts\n\n"
        "👉 Join: @Cricket_Thrill_Alert_Bot\n\n"
        "📱 WhatsApp Channel: Coming Soon!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# ─────────────────────────────────────────
# HELP
# ─────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "❓ Help")
def handle_help(message):
    """Help message dikhao"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
        types.InlineKeyboardButton("⚙️ Settings", callback_data="settings")
    )
    
    bot.send_message(
        message.from_user.id,
        "❓ <b>How to Use Cricket Thrill Alert</b>\n\n"
        "• Tap <b>🏏 Live IPL Match</b> to check current game.\n"
        "• Tap <b>⚙️ Settings</b> to manage your preferences.\n"
        "• Tap <b>📢 Share Bot</b> to invite friends.\n"
        "• Tap <b>⭐ Give Feedback</b> to help us improve.\n\n"
        "🔔 <b>Alert Commands:</b>\n"
        "• /stop — Stop all alerts\n"
        "• /resume — Resume alerts\n\n"
        "Everything works through buttons. Just tap! 🏏",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# ─────────────────────────────────────────
# /STOP AND /RESUME COMMANDS
# ─────────────────────────────────────────

@bot.message_handler(commands=["stop"])
def handle_stop_command(message):
    """Alerts band karo"""
    stop_notifications(message.from_user.id)
    bot.send_message(
        message.from_user.id,
        "🔕 Alerts stopped. Send /resume to turn on again.",
        reply_markup=get_bottom_menu()
    )

@bot.message_handler(commands=["resume"])
def handle_resume_command(message):
    """Alerts resume karo"""
    resume_notifications(message.from_user.id)
    bot.send_message(
        message.from_user.id,
        "🔔 Alerts resumed! You will now get IPL 2026 alerts. 🏏",
        reply_markup=get_bottom_menu()
    )

# ─────────────────────────────────────────
# MATCH POLLING LOOP (Background Thread)
# ─────────────────────────────────────────

def match_poll_loop():
    """
    Background mein chalne wala loop
    Har 60 second mein IPL match check karo
    Thrill detect karo aur alerts bhejo
    """
    print("🔄 Match polling loop started")
    
    while True:
        try:
            # Live IPL match dhundo
            match = get_live_ipl_match()
            
            if not match:
                # Koi match nahi - 60 sec wait karo
                time.sleep(60)
                continue
            
            match_id = match["match_id"]
            
            # Naya match discovered?
            if current_match["match_id"] != match_id:
                # Naya match announcement
                current_match["match_id"] = match_id
                current_match["team1"] = match["team1"]
                current_match["team2"] = match["team2"]
                
                print(f"🏏 New IPL match: {match['team1']} vs {match['team2']}")
                
                announcement = (
                    f"🏏 <b>Match Alert!</b>\n\n"
                    f"<b>{match['team1']}</b> vs <b>{match['team2']}</b>\n"
                    f"IPL 2026 is now being monitored.\n\n"
                    f"I will alert you when something EXCITING happens!\n"
                    f"Tap 🏏 Live IPL Match to see the live score."
                )
                
                broadcast_message(announcement)
            
            # Scorecard lo aur thrills detect karo
            scorecard = get_match_scorecard(match_id)
            innings_data = parse_current_innings(scorecard)
            
            if innings_data:
                alerts = detect_thrills(match_id, innings_data)
                
                for alert in alerts:
                    print(f"⚡ Thrill detected: {alert['type']}")
                    
                    if alert["is_mega"]:
                        # SOS mode - repeat alert
                        start_sos_for_all(alert["message"])
                    else:
                        # Normal alert - ek baar bhejo
                        broadcast_message(alert["message"])
        
        except Exception as e:
            print(f"❌ Poll loop error: {e}")
        
        # 60 second wait karo
        time.sleep(60)

# ─────────────────────────────────────────
# BOT START
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("🏏 Cricket Thrill Alert Bot starting...")
    
    # Database setup
    setup_database()
    
    # Google Sheets headers setup
    setup_sheet_headers()
    
    # Background match polling thread start karo
    poll_thread = threading.Thread(target=match_poll_loop, daemon=True)
    poll_thread.start()
    
    print("✅ Bot is running! Press Ctrl+C to stop.")
    
    # Bot polling start karo (ye forever chalta hai)
    bot.infinity_polling(timeout=60, long_polling_timeout=60)