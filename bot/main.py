import os
import time
import threading
import requests as req
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import TeleBot, types
from match_engine import (
    get_live_ipl_match,
    debug_ipl_status,
    get_match_scorecard,
    parse_current_innings,
    detect_thrills
)
from ipl_schedule import (
    is_match_time_now,
    get_todays_matches,
    format_schedule_message,
    get_schedule
)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing!")

bot = TeleBot(TOKEN)

# Users jo alerts chahte hain
alert_users = set()

# Current match tracking
current_match = {
    "match_id": None,
    "toss_notified": False,
    "result_notified": False
}

# ─────────────────────────────────────────
# WEB SERVER
# ─────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Thrill Alert Running")

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
    print(f"Web server on port {port}")
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
# BROADCAST
# ─────────────────────────────────────────

def broadcast(text):
    """Saare subscribed users ko message bhejo"""
    for uid in list(alert_users):
        try:
            bot.send_message(uid, text, parse_mode="HTML")
            time.sleep(0.05)
        except Exception:
            pass

# ─────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────

@bot.message_handler(commands=["start"])
def start_cmd(message):
    uid = message.from_user.id
    name = message.from_user.first_name or "Cricket Fan"
    alert_users.add(uid)

    # Schedule fetch karo (agar pehle se nahi hai)
    get_schedule()

    today = get_todays_matches()
    match_info = ""
    if today:
        match_info = f"\n📅 Today {len(today)} IPL match(es) scheduled!"
    else:
        match_info = "\n📅 No IPL match today"

    bot.send_message(
        message.chat.id,
        f"🏏 <b>Welcome to Thrill Alert!</b>\n\n"
        f"Hi <b>{name}</b>! 👋\n"
        f"{match_info}\n\n"
        f"✅ You will get automatic alerts for:\n"
        f"• 🪙 Toss updates\n"
        f"• 🚨 Key wickets\n"
        f"• 💥 Batting collapses\n"
        f"• 🔴 Thriller finishes\n"
        f"• 🏆 Match results + Thrill Score\n\n"
        f"I only buzz when it MATTERS! 🔥\n\n"
        f"Debug: /debuglive",
        reply_markup=get_menu(),
        parse_mode="HTML"
    )


@bot.message_handler(func=lambda m: m.text == "📅 Today's Schedule")
def schedule_handler(message):
    alert_users.add(message.from_user.id)
    schedule_msg = format_schedule_message()
    bot.send_message(
        message.chat.id,
        schedule_msg,
        parse_mode="HTML"
    )


@bot.message_handler(commands=["debuglive"])
def debug_cmd(message):
    alert_users.add(message.from_user.id)
    report = debug_ipl_status()
    bot.send_message(
        message.chat.id,
        f"🔍 <b>Debug Report</b>\n\n<code>{report}</code>",
        parse_mode="HTML"
    )


@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def live_match_handler(message):
    alert_users.add(message.from_user.id)
    match = get_live_ipl_match()

    if not match:
        today = get_todays_matches()
        if today:
            bot.send_message(
                message.chat.id,
                "🏏 <b>Match not started yet</b>\n\n"
                "I will auto-notify when toss happens! 🪙\n"
                "Tap 📅 Today's Schedule to see match time.",
                parse_mode="HTML"
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ <b>No live IPL match right now</b>\n\n"
                "I will auto-alert when match starts! 🔔",
                parse_mode="HTML"
            )
        return

    msg = (
        f"🏏 <b>{match['team1']}</b> vs <b>{match['team2']}</b>\n\n"
        f"📊 {match['status']}\n"
    )

    if match.get("toss"):
        msg += f"🪙 Toss: {match['toss']}\n"

    msg += "\n✅ Thrill alerts are active!"

    bot.send_message(
        message.chat.id,
        msg,
        parse_mode="HTML"
    )


@bot.message_handler(func=lambda m: True)
def catch_all(message):
    alert_users.add(message.from_user.id)
    bot.send_message(
        message.chat.id,
        "Tap the buttons below 👇",
        reply_markup=get_menu()
    )

# ─────────────────────────────────────────
# SMART THRILL POLLING ENGINE
# ─────────────────────────────────────────

def calculate_thrill_score(match_data):
    """
    Match ka Thrill Score calculate karo (1-10)
    """
    score = 3  # Base score

    if not match_data:
        return score

    score_list = match_data.get("score", [])
    status = match_data.get("status", "") or ""

    # Close margin
    if "1 wkt" in status or "1 run" in status:
        score += 4
    elif "2 wkt" in status or "2 run" in status:
        score += 3
    elif "super over" in status.lower():
        score += 5
    elif "tie" in status.lower():
        score += 5
    elif "3 wkt" in status or "3 run" in status:
        score += 2

    # High scoring
    if score_list:
        first = score_list[0]
        first_runs = int(first.get("r", 0) or 0)
        if first_runs >= 200:
            score += 2
        elif first_runs >= 180:
            score += 1

    # Collapse
    for innings in score_list:
        wickets = int(innings.get("w", 0) or 0)
        runs = int(innings.get("r", 0) or 0)
        if wickets >= 8 and runs < 140:
            score += 2

    return min(score, 10)


def thrill_poll_loop():
    """
    Smart polling loop:
    - Match nahi hai = 0 API calls
    - Normal game = 20 min intervals
    - Death overs = 5 min intervals
    - Thriller = 2 min intervals
    - Match khatam = result + sleep
    """
    print("🚀 Smart Thrill Engine Started")

    # Schedule fetch karo startup pe (1 call)
    get_schedule()

    while True:
        try:
            now = datetime.now()

            # ─── SLEEP MODE ───
            if not is_match_time_now():
                hour = now.hour

                # Deep sleep: midnight to 2 PM
                if 0 <= hour < 14:
                    print(f"😴 Deep sleep - {hour}:00")
                    time.sleep(3600)  # 1 hour
                else:
                    print(f"😴 No match window - {hour}:00")
                    time.sleep(1800)  # 30 min
                continue

            # ─── MATCH TIME - API CALL ───
            match = get_live_ipl_match()

            # Match not started yet
            if not match:
                print("⏰ Match window but not live yet")
                time.sleep(600)  # 10 min
                continue

            mid = match["match_id"]

            # ─── NEW MATCH DETECTED ───
            if current_match["match_id"] != mid:
                current_match["match_id"] = mid
                current_match["toss_notified"] = False
                current_match["result_notified"] = False

                print(f"🏏 New match: {match['team1']} vs {match['team2']}")

                # Toss notification
                toss_text = match.get("toss", "")
                if toss_text:
                    broadcast(
                        f"🪙 <b>TOSS UPDATE!</b>\n\n"
                        f"<b>{match['team1']}</b> vs <b>{match['team2']}</b>\n\n"
                        f"🪙 {toss_text}\n\n"
                        f"Match starting soon! 🏏"
                    )
                    current_match["toss_notified"] = True
                else:
                    broadcast(
                        f"🏏 <b>Match Alert!</b>\n\n"
                        f"<b>{match['team1']}</b> vs "
                        f"<b>{match['team2']}</b>\n\n"
                        f"Monitoring for THRILLS! 👀"
                    )

            # ─── SCORECARD CHECK ───
            scard = get_match_scorecard(mid)

            if not scard:
                time.sleep(600)
                continue

            data = parse_current_innings(scard)

            # ─── MATCH COMPLETE - RESULT ───
            match_status = (scard.get("status", "") or "").lower()
            if (
                "won" in match_status or
                "tie" in match_status or
                "no result" in match_status
            ) and not current_match["result_notified"]:

                # Thrill Score
                thrill = calculate_thrill_score(scard)
                thrill_bar = "🔥" * thrill + "⬜" * (10 - thrill)

                # Score summary
                score_lines = []
                for innings in scard.get("score", []):
                    inning_name = innings.get("inning", "") or ""
                    r = innings.get("r", 0)
                    w = innings.get("w", 0)
                    o = innings.get("o", 0)
                    score_lines.append(f"  {inning_name}: {r}/{w} ({o} ov)")

                scores_text = "\n".join(score_lines)

                broadcast(
                    f"🏆 <b>MATCH RESULT</b>\n\n"
                    f"{scard.get('status', 'Match Over')}\n\n"
                    f"📊 <b>Scorecard:</b>\n{scores_text}\n\n"
                    f"🔥 <b>THRILL RATING: {thrill}/10</b>\n"
                    f"{thrill_bar}\n\n"
                    f"{'🔴 What a match!' if thrill >= 7 else '🏏 Good game!' if thrill >= 4 else '😴 One sided affair'}"
                )

                current_match["result_notified"] = True
                current_match["match_id"] = None

                # Match khatam - next match tak sleep
                print("🏆 Match over - sleeping till next match")
                time.sleep(3600)
                continue

            # ─── THRILL DETECTION ───
            if data:
                overs = data["overs"]
                wickets = data["wickets"]
                innings_id = data["innings_id"]
                target = data.get("target")
                req_rate = data.get("req_rate", 0)

                # Detect thrills
                alerts = detect_thrills(mid, data)
                for alert in alerts:
                    print(f"🎯 {alert['type']}")
                    broadcast(alert["message"])

                # ─── SMART POLLING SPEED ───

                # 2nd innings chase
                if innings_id >= 2 and target:
                    runs_needed = target - data["runs"]
                    balls_left = max(1, int((20 - overs) * 6))

                    # SUPER CLOSE: Last 3 overs + <30 needed
                    if overs >= 17.0 and 0 < runs_needed <= 30:
                        wait = 120  # 2 min
                        print(f"🔥 NAIL BITER - 2 min")

                    # CLOSE: Last 5 overs + <60 needed
                    elif overs >= 15.0 and 0 < runs_needed <= 60:
                        wait = 300  # 5 min
                        print(f"🔴 THRILLER ZONE - 5 min")

                    # STEEP CHASE: Required rate 14+
                    elif req_rate >= 14.0 and overs >= 10.0:
                        wait = 300  # 5 min
                        print(f"📈 STEEP CHASE - 5 min")

                    # Normal chase
                    else:
                        wait = 900  # 15 min
                        print(f"🏏 Normal chase - 15 min")

                # 1st innings
                elif innings_id == 1:
                    # Collapse happening
                    if wickets >= 5 and overs <= 15:
                        wait = 300  # 5 min
                        print(f"😱 Collapse watch - 5 min")

                    # Death overs
                    elif overs >= 16.0:
                        wait = 300  # 5 min
                        print(f"💥 Death overs - 5 min")

                    # Normal batting
                    else:
                        wait = 1200  # 20 min
                        print(f"😎 Normal batting - 20 min")

                else:
                    wait = 600

            else:
                # Innings break ya toss
                wait = 600  # 10 min
                print(f"⏸️ Break/Toss - 10 min")

            time.sleep(wait)

        except Exception as e:
            print(f"❌ Poll error: {e}")
            time.sleep(600)

# ─────────────────────────────────────────
# START
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("Starting Thrill Alert Bot...")

    # Web server
    threading.Thread(target=run_server, daemon=True).start()

    # Webhook clear
    try:
        req.get(
            f"https://api.telegram.org/bot{TOKEN}"
            f"/deleteWebhook?drop_pending_updates=true",
            timeout=10
        )
        print("Webhook cleared")
    except Exception:
        pass

    time.sleep(2)

    # Smart Thrill Engine
    threading.Thread(target=thrill_poll_loop, daemon=True).start()
    print("Smart Thrill Engine started")

    print("Bot polling started...")
    bot.polling(none_stop=True, timeout=30, interval=1)
