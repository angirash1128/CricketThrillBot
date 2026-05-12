# main.py
# Thrill Alert Bot - Professional Cached Architecture
# User clicks = 0 API calls
# Background polling = smart API calls
# Automatic thrill notifications

import os
import time
import threading
import requests as req
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import TeleBot, types

from ipl_schedule import (
    CACHE,
    get_cache,
    update_cache,
    fetch_schedule,
    get_todays_matches,
    get_upcoming_matches,
    is_match_time_now,
    format_schedule_message
)

from match_engine import (
    fetch_live_match,
    fetch_scorecard,
    get_live_ipl_match,
    get_match_scorecard,
    parse_current_innings,
    detect_thrills,
    debug_ipl_status
)

# ─────────────────────────────────────────
# BOT SETUP
# ─────────────────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing!")

bot = TeleBot(TOKEN)

# Users jo alerts chahte hain
alert_users = set()

# ─────────────────────────────────────────
# WEB SERVER (Render ke liye zaroori)
# ─────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Thrill Alert Bot Running!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass


def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"✅ Web server on port {port}")
    server.serve_forever()


# ─────────────────────────────────────────
# MENU
# ─────────────────────────────────────────

def get_menu():
    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        is_persistent=True
    )
    kb.row("🏏 Live IPL Match")
    kb.row("📅 Today's Schedule")
    return kb


# ─────────────────────────────────────────
# BROADCAST (0 API calls)
# ─────────────────────────────────────────

def broadcast(text):
    """Saare subscribed users ko message bhejo"""
    count = 0
    for uid in list(alert_users):
        try:
            bot.send_message(uid, text, parse_mode="HTML")
            count += 1
            time.sleep(0.05)
        except Exception:
            pass
    if count > 0:
        print(f"📢 Broadcast to {count} users")


# ─────────────────────────────────────────
# THRILL SCORE
# ─────────────────────────────────────────

def calculate_thrill_score(match_data):
    """Match ka Thrill Score (1-10)"""
    score = 3

    if not match_data:
        return score

    status = (match_data.get("status", "") or "").lower()
    score_list = match_data.get("score", [])

    if "1 wkt" in status or "1 run" in status:
        score += 4
    elif "2 wkt" in status or "2 run" in status:
        score += 3
    elif "3 wkt" in status or "3 run" in status:
        score += 2
    elif "super over" in status:
        score += 5
    elif "tie" in status:
        score += 5

    if score_list:
        first = score_list[0]
        first_runs = int(first.get("r", 0) or 0)
        if first_runs >= 220:
            score += 2
        elif first_runs >= 190:
            score += 1

    if score_list and len(score_list) >= 2:
        second = score_list[-1]
        overs = float(second.get("o", 20) or 20)
        if overs >= 19.5:
            score += 1

    return min(score, 10)


# ─────────────────────────────────────────
# BOT HANDLERS (0 API calls - cache se)
# ─────────────────────────────────────────

@bot.message_handler(commands=["start"])
def start_cmd(message):
    uid = message.from_user.id
    name = message.from_user.first_name or "Cricket Fan"
    alert_users.add(uid)

    # Agar schedule cache empty hai to fetch karo
    if not get_cache()["schedule_fetched"]:
        print("📅 Fetching schedule on /start ...")
        fetch_schedule()

    today = get_todays_matches()

    if today:
        match_info = f"\n📅 {len(today)} IPL match(es) today!"
    else:
        match_info = "\n📅 No IPL match today"

    bot.send_message(
        message.chat.id,
        f"🏏 <b>Welcome to Thrill Alert!</b>\n\n"
        f"Hi <b>{name}</b>! 👋"
        f"{match_info}\n\n"
        f"✅ <b>Auto alerts active for:</b>\n"
        f"• 🪙 Toss result\n"
        f"• 😱 Batting collapse\n"
        f"• 💥 Explosive batting\n"
        f"• 🔴 Thriller chase\n"
        f"• 🔥 Nail biter finish\n"
        f"• 🏆 Match result + Thrill Score\n\n"
        f"<i>I only buzz when it MATTERS!</i> 🔥",
        reply_markup=get_menu(),
        parse_mode="HTML"
    )


@bot.message_handler(func=lambda m: m.text == "📅 Today's Schedule")
def schedule_handler(message):
    """Schedule - 0 API calls (cache se)"""
    alert_users.add(message.from_user.id)

    # Agar schedule load nahi hua to fetch karo
    if not get_cache()["schedule_fetched"]:
        print("📅 Fetching schedule on button click ...")
        fetch_schedule()

    # Agar fetch ke baad bhi nahi mila
    if not get_cache()["schedule_fetched"] or len(get_cache()["schedule"]) == 0:
        bot.send_message(
            message.chat.id,
            "⚠️ Schedule could not be loaded.\n"
            "Please try again in 2 minutes.",
            parse_mode="HTML"
        )
        return

    schedule_msg = format_schedule_message()
    bot.send_message(
        message.chat.id,
        schedule_msg,
        parse_mode="HTML"
    )


@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def live_match_handler(message):
    """Live match - 0 API calls (cache se)"""
    alert_users.add(message.from_user.id)

    match = get_live_ipl_match()

    if not match:
        today = get_todays_matches()
        if today:
            schedule_msg = format_schedule_message()
            bot.send_message(
                message.chat.id,
                f"🏏 <b>Match not started yet</b>\n\n"
                f"I will auto-notify when toss happens! 🪙\n\n"
                f"{schedule_msg}",
                parse_mode="HTML"
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ <b>No live IPL match right now</b>\n\n"
                "I will auto-alert when match starts! 🔔\n\n"
                "Tap 📅 Today's Schedule for upcoming matches.",
                parse_mode="HTML"
            )
        return

    # Live match info cache se
    msg_lines = [
        f"🏏 <b>{match['team1']}</b> vs <b>{match['team2']}</b>\n"
    ]

    if match.get("toss"):
        msg_lines.append(f"🪙 {match['toss']}\n")

    if match.get("t1_score"):
        msg_lines.append(f"📊 {match['team1']}: {match['t1_score']}")
    if match.get("t2_score"):
        msg_lines.append(f"📊 {match['team2']}: {match['t2_score']}")

    msg_lines.append(f"\n🔴 {match['status']}")

    innings = get_cache().get("live_innings")
    if innings:
        msg_lines.append(f"\n📈 Run Rate: {innings['run_rate']}")
        if innings.get("req_rate", 0) > 0:
            msg_lines.append(f"⚡ Required Rate: {innings['req_rate']}")

    last_call = get_cache()["last_api_call"]
    if last_call:
        msg_lines.append(f"\n📡 Updated: {last_call}")

    msg_lines.append("\n✅ Thrill alerts are active!")

    bot.send_message(
        message.chat.id,
        "\n".join(msg_lines),
        parse_mode="HTML"
    )


@bot.message_handler(commands=["debug"])
def debug_cmd(message):
    """Debug - cache status (0 API calls)"""
    alert_users.add(message.from_user.id)
    report = debug_ipl_status()
    bot.send_message(
        message.chat.id,
        f"🔍 <b>Cache Status</b>\n\n<code>{report}</code>",
        parse_mode="HTML"
    )


@bot.message_handler(func=lambda m: True)
def catch_all(message):
    alert_users.add(message.from_user.id)
    bot.send_message(
        message.chat.id,
        "Use the buttons below 👇",
        reply_markup=get_menu()
    )


# ─────────────────────────────────────────
# SMART POLLING ENGINE
# ─────────────────────────────────────────

def smart_poll_loop():
    """
    Professional polling:

    API Budget (90 calls/day):
    Schedule: 2 calls (startup)
    Single match: ~20-25 calls
    Double header: ~40-45 calls
    Buffer: ~25 calls spare

    Intervals:
    No match = 0 calls (sleep)
    Waiting for start = 10 min
    Normal batting = 20 min
    Death overs = 5 min
    Collapse = 5 min
    Thriller chase = 5 min
    Nail biter = 2 min
    Match over = sleep
    """
    print("🚀 Smart Polling Engine Started")

    # Startup schedule fetch
    print("📅 Fetching IPL Schedule ...")
    fetch_schedule()

    while True:
        try:
            now = datetime.now()
            cache = get_cache()

            # ─── DEEP SLEEP (12 AM to 2 PM) ───
            if now.hour < 14:
                print(f"😴 Deep sleep - {now.strftime('%H:%M')}")
                time.sleep(3600)
                continue

            # ─── NO MATCH WINDOW ───
            if not is_match_time_now():
                print(f"😴 No match window - {now.strftime('%H:%M')}")
                time.sleep(1800)
                continue

            # ─── MATCH WINDOW ACTIVE ───
            # 1 API call
            match = fetch_live_match()

            if not match:
                print("⏰ Waiting for match to start")
                time.sleep(600)
                continue

            mid = match["match_id"]

            # ─── NEW MATCH ───
            if cache["current_match_id"] != mid:
                update_cache("current_match_id", mid)
                update_cache("match_started", True)
                update_cache("match_ended", False)
                update_cache("toss_notified", False)
                update_cache("result_notified", False)
                update_cache("live_scorecard", None)
                update_cache("live_innings", None)

                print(f"🏏 New: {match['team1']} vs {match['team2']}")

                toss = match.get("toss", "")
                if toss:
                    broadcast(
                        f"🪙 <b>TOSS UPDATE!</b>\n\n"
                        f"<b>{match['team1']}</b> vs "
                        f"<b>{match['team2']}</b>\n\n"
                        f"{toss}\n\n"
                        f"Match starting soon! 🏏"
                    )
                    update_cache("toss_notified", True)
                else:
                    broadcast(
                        f"🏏 <b>MATCH STARTING!</b>\n\n"
                        f"<b>{match['team1']}</b> vs "
                        f"<b>{match['team2']}</b>\n\n"
                        f"Monitoring for THRILLS! 👀🔥"
                    )

            # Toss late mila
            elif not cache["toss_notified"] and match.get("toss"):
                broadcast(
                    f"🪙 <b>TOSS!</b>\n\n"
                    f"{match['toss']}\n\n"
                    f"Match is ON! 🏏"
                )
                update_cache("toss_notified", True)

            # ─── SCORECARD (1 API call) ───
            scard = fetch_scorecard(mid)

            if not scard:
                time.sleep(600)
                continue

            # ─── MATCH COMPLETE ───
            match_status = (scard.get("status", "") or "").lower()
            is_complete = (
                "won" in match_status or
                "tie" in match_status or
                "no result" in match_status or
                "abandoned" in match_status
            )

            if is_complete and not cache["result_notified"]:
                thrill = calculate_thrill_score(scard)
                thrill_bar = "🔥" * thrill + "⬜" * (10 - thrill)

                score_lines = []
                for innings in scard.get("score", []):
                    inning_name = innings.get("inning", "") or ""
                    r = innings.get("r", 0)
                    w = innings.get("w", 0)
                    o = innings.get("o", 0)
                    if inning_name:
                        score_lines.append(
                            f"  {inning_name}: {r}/{w} ({o} ov)")

                scores_text = "\n".join(score_lines)

                if thrill >= 8:
                    comment = "🔴 WHAT A MATCH! Must watch highlights!"
                elif thrill >= 6:
                    comment = "🏏 Good contest! Worth watching."
                elif thrill >= 4:
                    comment = "😊 Decent game."
                else:
                    comment = "😴 One-sided affair."

                broadcast(
                    f"🏆 <b>MATCH RESULT</b>\n\n"
                    f"{scard.get('status', 'Match Over')}\n\n"
                    f"📊 <b>Scorecard:</b>\n"
                    f"{scores_text}\n\n"
                    f"🔥 <b>THRILL RATING: {thrill}/10</b>\n"
                    f"{thrill_bar}\n\n"
                    f"{comment}"
                )

                update_cache("result_notified", True)
                update_cache("match_ended", True)
                update_cache("current_match_id", None)
                update_cache("live_match", None)
                update_cache("live_scorecard", None)
                update_cache("live_innings", None)

                print(f"🏆 Match over! Thrill: {thrill}/10")
                time.sleep(3600)
                continue

            # ─── THRILL DETECTION ───
            data = parse_current_innings(scard)

            if data:
                alerts = detect_thrills(mid, data)
                for alert in alerts:
                    print(f"🎯 {alert['type']}")
                    broadcast(alert["message"])

                # ─── SMART WAIT ───
                overs = data["overs"]
                wickets = data["wickets"]
                innings_id = data["innings_id"]
                target = data.get("target")
                req_rate = data.get("req_rate", 0)

                if innings_id >= 2 and target:
                    runs_needed = target - data["runs"]

                    if overs >= 17.0 and 0 < runs_needed <= 30:
                        wait = 120
                        print("🔥 NAIL BITER - 2 min")
                    elif overs >= 15.0 and 0 < runs_needed <= 60:
                        wait = 300
                        print("🔴 THRILLER - 5 min")
                    elif req_rate >= 14.0 and overs >= 10.0:
                        wait = 300
                        print("📈 STEEP CHASE - 5 min")
                    else:
                        wait = 900
                        print("🏏 Normal chase - 15 min")
                else:
                    if wickets >= 5 and overs <= 15:
                        wait = 300
                        print("😱 Collapse watch - 5 min")
                    elif overs >= 16.0:
                        wait = 300
                        print("💥 Death overs - 5 min")
                    else:
                        wait = 1200
                        print("😎 Normal - 20 min")
            else:
                wait = 600
                print("⏸️ Break - 10 min")

            time.sleep(wait)

        except Exception as e:
            print(f"❌ Poll error: {e}")
            time.sleep(600)


# ─────────────────────────────────────────
# DAILY SCHEDULE REFRESH
# ─────────────────────────────────────────

def daily_schedule_refresh():
    """Roz 12 AM schedule refresh"""
    while True:
        try:
            now = datetime.now()
            if now.hour == 0 and now.minute < 30:
                print("🔄 Daily schedule refresh")
                update_cache("schedule_fetched", False)
                update_cache("schedule", [])
                fetch_schedule()
                time.sleep(3600)
            else:
                time.sleep(1800)
        except Exception as e:
            print(f"Refresh error: {e}")
            time.sleep(3600)


# ─────────────────────────────────────────
# START
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("🏏 Starting Thrill Alert Bot...")

    # Web server
    threading.Thread(target=run_server, daemon=True).start()

    # Webhook clear
    try:
        req.get(
            f"https://api.telegram.org/bot{TOKEN}"
            f"/deleteWebhook?drop_pending_updates=true",
            timeout=10
        )
        print("✅ Webhook cleared")
    except Exception:
        pass

    time.sleep(2)

    # Smart polling engine
    threading.Thread(target=smart_poll_loop, daemon=True).start()
    print("✅ Smart Polling Engine started")

    # Daily schedule refresh
    threading.Thread(target=daily_schedule_refresh, daemon=True).start()
    print("✅ Daily Refresh started")

    print("✅ Bot polling started!")
    bot.polling(none_stop=True, timeout=30, interval=1)
