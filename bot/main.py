# main.py
# Thrill Alert Bot - Professional Cached Architecture
# User clicks pe 0 API calls
# Background polling se data fetch + cache
# Thrill alerts automatic broadcast

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

# Subscribed users (jo alerts chahte hain)
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
# BROADCAST (Saare users ko)
# ─────────────────────────────────────────

def broadcast(text):
    """
    Saare subscribed users ko message bhejo
    0 API calls
    """
    count = 0
    for uid in list(alert_users):
        try:
            bot.send_message(uid, text, parse_mode="HTML")
            count += 1
            time.sleep(0.05)
        except Exception:
            pass
    if count > 0:
        print(f"📢 Broadcast sent to {count} users")


# ─────────────────────────────────────────
# THRILL SCORE CALCULATOR
# ─────────────────────────────────────────

def calculate_thrill_score(match_data):
    """
    Match ka Thrill Score calculate karo (1-10)
    Match result ke baad call hoga
    """
    score = 3  # Base

    if not match_data:
        return score

    status = (match_data.get("status", "") or "").lower()
    score_list = match_data.get("score", [])

    # Super close finish
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

    # High scoring match
    if score_list:
        first = score_list[0]
        first_runs = int(first.get("r", 0) or 0)
        if first_runs >= 220:
            score += 2
        elif first_runs >= 190:
            score += 1

    # Last over finish check
    if score_list and len(score_list) >= 2:
        second = score_list[-1]
        overs = float(second.get("o", 20) or 20)
        if overs >= 19.5:
            score += 1

    return min(score, 10)


# ─────────────────────────────────────────
# BOT HANDLERS
# ─────────────────────────────────────────

@bot.message_handler(commands=["start"])
def start_cmd(message):
    uid = message.from_user.id
    name = message.from_user.first_name or "Cricket Fan"
    alert_users.add(uid)

    # Today's matches - 0 API calls (cache se)
    today = get_todays_matches()

    if today:
        match_count = len(today)
        match_info = f"\n📅 {match_count} IPL match(es) today!"
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
    """
    Schedule dikhao - 0 API calls
    Cache se data return karo
    """
    alert_users.add(message.from_user.id)

    # Agar schedule cache empty hai
    # to user ko batao (background mein fetch hoga)
    if not get_cache()["schedule_fetched"]:
        bot.send_message(
            message.chat.id,
            "⏳ Schedule loading...\n"
            "Please try again in 30 seconds.",
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
    """
    Live match dikhao - 0 API calls
    Cache se data return karo
    """
    alert_users.add(message.from_user.id)

    # Cache se data lo
    match = get_live_ipl_match()

    if not match:
        today = get_todays_matches()
        if today:
            # Match scheduled but not started
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
                "Tap 📅 Today's Schedule to check upcoming matches.",
                parse_mode="HTML"
            )
        return

    # Live match info - cache se
    msg_lines = [
        f"🏏 <b>{match['team1']}</b> vs <b>{match['team2']}</b>\n"
    ]

    # Toss info
    if match.get("toss"):
        msg_lines.append(f"🪙 {match['toss']}\n")

    # Current scores
    if match.get("t1_score"):
        msg_lines.append(f"📊 {match['team1']}: {match['t1_score']}")
    if match.get("t2_score"):
        msg_lines.append(f"📊 {match['team2']}: {match['t2_score']}")

    # Status
    msg_lines.append(f"\n🔴 {match['status']}")

    # Innings data
    innings = get_cache().get("live_innings")
    if innings:
        msg_lines.append(
            f"\n📈 Run Rate: {innings['run_rate']}"
        )
        if innings.get("req_rate", 0) > 0:
            msg_lines.append(
                f"⚡ Required Rate: {innings['req_rate']}"
            )

    # Last updated
    last_call = get_cache()["last_api_call"]
    if last_call:
        msg_lines.append(f"\n📡 Last updated: {last_call}")

    msg_lines.append("\n✅ Thrill alerts are active!")

    bot.send_message(
        message.chat.id,
        "\n".join(msg_lines),
        parse_mode="HTML"
    )


@bot.message_handler(commands=["debug"])
def debug_cmd(message):
    """
    Debug - cache status dikhao
    0 API calls (cache se)
    """
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
    Professional polling loop:

    API Budget Plan (90 calls/day):
    - Schedule fetch: 2 calls (startup only)
    - Match window polling: ~20-30 calls/match
    - Double header: ~50 calls total
    - Buffer: 40 calls

    Polling intervals:
    - No match time: 0 calls (sleep)
    - Match not started: 1 call per 10 min (check toss)
    - Normal game: 1 call per 20 min
    - Death overs: 1 call per 5 min
    - Thriller zone: 1 call per 2 min
    - Match over: 0 calls (sleep)
    """
    print("🚀 Smart Polling Engine Started")

    # ─── STARTUP: Schedule fetch ───
    print("📅 Fetching IPL Schedule...")
    fetch_schedule()

    while True:
        try:
            now = datetime.now()
            cache = get_cache()

            # ─── SLEEP MODE ───
            # Raat 12 baje se dopahar 2 baje tak = ZERO calls
            if now.hour < 14 or now.hour >= 24:
                print(f"😴 Deep sleep - {now.strftime('%H:%M')}")
                time.sleep(3600)  # 1 ghanta
                continue

            # ─── CHECK MATCH WINDOW ───
            if not is_match_time_now():
                print(f"😴 No match window - {now.strftime('%H:%M')}")
                time.sleep(1800)  # 30 min
                continue

            # ─── MATCH WINDOW ACTIVE ───
            # 1 API call - live match check
            match = fetch_live_match()

            # ─── NO LIVE MATCH YET ───
            if not match:
                # Match scheduled but toss nahi hua
                print("⏰ Match window - waiting for match to start")
                time.sleep(600)  # 10 min
                continue

            mid = match["match_id"]

            # ─── NEW MATCH DETECTED ───
            if cache["current_match_id"] != mid:
                update_cache("current_match_id", mid)
                update_cache("match_started", True)
                update_cache("match_ended", False)
                update_cache("toss_notified", False)
                update_cache("result_notified", False)
                update_cache("live_scorecard", None)
                update_cache("live_innings", None)

                print(f"🏏 New match: {match['team1']} vs {match['team2']}")

                # Toss notification
                toss_text = match.get("toss", "")
                if toss_text and not cache["toss_notified"]:
                    broadcast(
                        f"🪙 <b>TOSS UPDATE!</b>\n\n"
                        f"<b>{match['team1']}</b> vs "
                        f"<b>{match['team2']}</b>\n\n"
                        f"{toss_text}\n\n"
                        f"Match starting soon! 🏏\n"
                        f"I will alert you for every thrill! 🔥"
                    )
                    update_cache("toss_notified", True)
                else:
                    broadcast(
                        f"🏏 <b>MATCH STARTING!</b>\n\n"
                        f"<b>{match['team1']}</b> vs "
                        f"<b>{match['team2']}</b>\n\n"
                        f"Monitoring for THRILLS! 👀🔥"
                    )

            # Toss update (agar pehle nahi mila)
            elif not cache["toss_notified"] and match.get("toss"):
                broadcast(
                    f"🪙 <b>TOSS UPDATE!</b>\n\n"
                    f"<b>{match['team1']}</b> vs "
                    f"<b>{match['team2']}</b>\n\n"
                    f"{match['toss']}\n\n"
                    f"Match is ON! 🏏"
                )
                update_cache("toss_notified", True)

            # ─── SCORECARD FETCH ───
            # 1 API call
            scard = fetch_scorecard(mid)

            if not scard:
                time.sleep(600)
                continue

            # ─── MATCH COMPLETE CHECK ───
            match_status = (scard.get("status", "") or "").lower()
            is_complete = (
                "won" in match_status or
                "tie" in match_status or
                "no result" in match_status or
                "abandoned" in match_status
            )

            if is_complete and not cache["result_notified"]:
                # Thrill score calculate karo
                thrill = calculate_thrill_score(scard)
                thrill_bar = "🔥" * thrill + "⬜" * (10 - thrill)

                # Score summary
                score_lines = []
                for innings in scard.get("score", []):
                    inning_name = innings.get("inning", "") or ""
                    r = innings.get("r", 0)
                    w = innings.get("w", 0)
                    o = innings.get("o", 0)
                    if inning_name:
                        score_lines.append(
                            f"  {inning_name}: {r}/{w} ({o} ov)"
                        )

                scores_text = "\n".join(score_lines)

                # Thrill comment
                if thrill >= 8:
                    thrill_comment = "🔴 WHAT A MATCH! Don't miss the highlights!"
                elif thrill >= 6:
                    thrill_comment = "🏏 Good contest! Worth watching highlights."
                elif thrill >= 4:
                    thrill_comment = "😊 Decent game."
                else:
                    thrill_comment = "😴 One-sided affair."

                broadcast(
                    f"🏆 <b>MATCH RESULT</b>\n\n"
                    f"{scard.get('status', 'Match Over')}\n\n"
                    f"📊 <b>Scorecard:</b>\n"
                    f"{scores_text}\n\n"
                    f"🔥 <b>THRILL RATING: {thrill}/10</b>\n"
                    f"{thrill_bar}\n\n"
                    f"{thrill_comment}"
                )

                update_cache("result_notified", True)
                update_cache("match_ended", True)
                update_cache("current_match_id", None)
                update_cache("live_match", None)
                update_cache("live_scorecard", None)
                update_cache("live_innings", None)

                print(f"🏆 Match over! Thrill: {thrill}/10")

                # Match khatam - next match tak sleep
                time.sleep(3600)
                continue

            # ─── THRILL DETECTION ───
            data = parse_current_innings(scard)

            if data:
                alerts = detect_thrills(mid, data)
                for alert in alerts:
                    print(f"🎯 Thrill: {alert['type']}")
                    broadcast(alert["message"])

                # ─── SMART POLLING SPEED ───
                overs = data["overs"]
                wickets = data["wickets"]
                innings_id = data["innings_id"]
                target = data.get("target")
                req_rate = data.get("req_rate", 0)

                # 2nd innings chase
                if innings_id >= 2 and target:
                    runs_needed = target - data["runs"]

                    if overs >= 17.0 and 0 < runs_needed <= 30:
                        # Last 3 overs - very close
                        wait = 120  # 2 min
                        print("🔥 NAIL BITER - 2 min")

                    elif overs >= 15.0 and 0 < runs_needed <= 60:
                        # Last 5 overs - close
                        wait = 300  # 5 min
                        print("🔴 THRILLER ZONE - 5 min")

                    elif req_rate >= 14.0 and overs >= 10.0:
                        # Steep chase
                        wait = 300  # 5 min
                        print("📈 STEEP CHASE - 5 min")

                    else:
                        # Normal chase
                        wait = 900  # 15 min
                        print("🏏 Normal chase - 15 min")

                # 1st innings
                else:
                    if wickets >= 5 and overs <= 15:
                        # Collapse watch
                        wait = 300  # 5 min
                        print("😱 Collapse watch - 5 min")

                    elif overs >= 16.0:
                        # Death overs
                        wait = 300  # 5 min
                        print("💥 Death overs - 5 min")

                    else:
                        # Normal batting
                        wait = 1200  # 20 min
                        print("😎 Normal batting - 20 min")

            else:
                # Innings break / toss time
                wait = 600  # 10 min
                print("⏸️ Break - 10 min")

            time.sleep(wait)

        except Exception as e:
            print(f"❌ Poll error: {e}")
            time.sleep(600)


# ─────────────────────────────────────────
# DAILY SCHEDULE REFRESH
# ─────────────────────────────────────────

def daily_schedule_refresh():
    """
    Roz raat 12 baje schedule refresh karo
    Sirf 2 API calls
    Playoffs/Finals ke liye
    """
    while True:
        try:
            now = datetime.now()

            # Raat 12 baje refresh
            if now.hour == 0 and now.minute < 30:
                print("🔄 Daily schedule refresh")
                update_cache("schedule_fetched", False)
                update_cache("schedule", [])
                fetch_schedule()
                time.sleep(3600)  # 1 ghanta wait
            else:
                time.sleep(1800)  # 30 min check

        except Exception as e:
            print(f"Schedule refresh error: {e}")
            time.sleep(3600)


# ─────────────────────────────────────────
# START
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("🏏 Starting Thrill Alert Bot...")

    # Web server start karo
    threading.Thread(
        target=run_server,
        daemon=True
    ).start()

    # Webhook clear karo
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
    threading.Thread(
        target=smart_poll_loop,
        daemon=True
    ).start()
    print("✅ Smart Polling Engine started")

    # Daily schedule refresh
    threading.Thread(
        target=daily_schedule_refresh,
        daemon=True
    ).start()
    print("✅ Daily Schedule Refresh started")

    print("✅ Bot polling started!")
    bot.polling(none_stop=True, timeout=30, interval=1)
