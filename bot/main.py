# main.py
# Thrill Alert Bot
# User clicks = 0 API calls (cache se)
# Background = controlled API calls only

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
    get_todays_matches,
    get_upcoming_matches,
    is_match_time_now,
    format_schedule_message,
)

from match_engine import (
    fetch_live_match,
    fetch_scorecard,
    get_live_ipl_match,
    parse_current_innings,
    detect_thrills,
    debug_ipl_status,
)

# ─────────────────────────────────────────
# BOT SETUP
# ─────────────────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN missing!")

bot = TeleBot(TOKEN)
alert_users = set()

# ─────────────────────────────────────────
# WEB SERVER
# ─────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Thrill Alert Running!")

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
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
    print(f"✅ Server on port {port}")


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def get_menu():
    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        is_persistent=True
    )
    kb.row("🏏 Live IPL Match")
    kb.row("📅 Today's Schedule")
    return kb


def broadcast(text):
    """0 API calls - sirf message bhejo"""
    count = 0
    for uid in list(alert_users):
        try:
            bot.send_message(uid, text, parse_mode="HTML")
            count += 1
            time.sleep(0.05)
        except Exception:
            pass
    if count > 0:
        print(f"📢 Sent to {count} users")


def calculate_thrill_score(scard):
    """Match thrill score 1-10"""
    score = 3
    if not scard:
        return score

    status = (scard.get("status", "") or "").lower()
    score_list = scard.get("score", [])

    if "1 wkt" in status or "1 run" in status:
        score += 4
    elif "2 wkt" in status or "2 run" in status:
        score += 3
    elif "3 wkt" in status or "3 run" in status:
        score += 2
    elif "super over" in status or "tie" in status:
        score += 5

    if score_list:
        first_runs = int(score_list[0].get("r", 0) or 0)
        if first_runs >= 220:
            score += 2
        elif first_runs >= 190:
            score += 1

    return min(score, 10)


# ─────────────────────────────────────────
# BOT HANDLERS (0 API calls)
# ─────────────────────────────────────────

@bot.message_handler(commands=["start"])
def start_cmd(message):
    uid = message.from_user.id
    name = message.from_user.first_name or "Cricket Fan"
    alert_users.add(uid)

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
        f"✅ <b>Auto alerts for:</b>\n"
        f"• 🪙 Toss result\n"
        f"• 😱 Batting collapse\n"
        f"• 🔴 Thriller chase\n"
        f"• 🔥 Nail biter finish\n"
        f"• 🏆 Match result + Thrill Score\n\n"
        f"<i>I only buzz when it MATTERS!</i> 🔥",
        reply_markup=get_menu(),
        parse_mode="HTML"
    )


@bot.message_handler(func=lambda m: m.text == "📅 Today's Schedule")
def schedule_handler(message):
    """0 API calls - hardcoded schedule se"""
    alert_users.add(message.from_user.id)
    schedule_msg = format_schedule_message()
    bot.send_message(
        message.chat.id,
        schedule_msg,
        parse_mode="HTML"
    )


@bot.message_handler(func=lambda m: m.text == "🏏 Live IPL Match")
def live_match_handler(message):
    """0 API calls - cache se"""
    alert_users.add(message.from_user.id)

    match = get_live_ipl_match()

    if not match:
        today = get_todays_matches()
        if today:
            bot.send_message(
                message.chat.id,
                f"🏏 <b>Match not started yet</b>\n\n"
                f"I will notify when toss happens! 🪙\n\n"
                f"{format_schedule_message()}",
                parse_mode="HTML"
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ <b>No live IPL match right now</b>\n\n"
                "Tap 📅 Today's Schedule for upcoming matches.",
                parse_mode="HTML"
            )
        return

    # Cache se data dikhao
    lines = [f"🏏 <b>{match['team1']}</b> vs <b>{match['team2']}</b>\n"]

    if match.get("toss"):
        lines.append(f"🪙 {match['toss']}\n")

    if match.get("t1_score"):
        lines.append(f"📊 {match['team1']}: {match['t1_score']}")
    if match.get("t2_score"):
        lines.append(f"📊 {match['team2']}: {match['t2_score']}")

    lines.append(f"\n🔴 {match['status']}")

    innings = get_cache().get("live_innings")
    if innings:
        lines.append(f"\n📈 Run Rate: {innings['run_rate']}")
        if innings.get("req_rate", 0) > 0:
            lines.append(f"⚡ Required Rate: {innings['req_rate']}")

    last = get_cache().get("last_updated")
    if last:
        lines.append(f"\n📡 Updated: {last}")

    lines.append("\n✅ Thrill alerts active!")

    bot.send_message(
        message.chat.id,
        "\n".join(lines),
        parse_mode="HTML"
    )


@bot.message_handler(commands=["debug"])
def debug_cmd(message):
    """Cache status - 0 API calls"""
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
        "Tap below 👇",
        reply_markup=get_menu()
    )


# ─────────────────────────────────────────
# SMART POLLING ENGINE
# Max 15-18 API calls per match
# ─────────────────────────────────────────

def smart_poll_loop():
    """
    Controlled polling:

    No match time   → 0 calls (sleep)
    Waiting start   → 1 call per 15 min
    Normal game     → 1 call per 25 min (2 calls per hour)
    Death overs     → 1 call per 8 min
    Thriller chase  → 1 call per 5 min
    Nail biter      → 1 call per 2 min

    Budget per match:
    Toss check:    2 calls
    1st innings:   5 calls (25 min each)
    Innings break: 0 calls
    2nd innings:   5 calls (15-25 min)
    Last 5 overs:  4 calls (5-8 min)
    Nail biter:    3 calls (2 min)
    ────────────────────────
    Total:        ~18 calls max
    """
    print("🚀 Smart Poll Started")

    while True:
        try:
            now = datetime.now()

            # ─── DEEP SLEEP (12 AM - 2 PM) ───
            if now.hour < 14:
                print(f"😴 Sleep {now.strftime('%H:%M')}")
                time.sleep(3600)
                continue

            # ─── NO MATCH WINDOW ───
            if not is_match_time_now():
                print(f"😴 No match {now.strftime('%H:%M')}")
                time.sleep(1800)
                continue

            # ─── MATCH WINDOW - 1 API call ───
            match = fetch_live_match()

            if not match:
                print("⏰ Waiting for match")
                time.sleep(900)  # 15 min
                continue

            mid = match["match_id"]
            cache = get_cache()

            # ─── NEW MATCH ───
            if cache["current_match_id"] != mid:
                update_cache("current_match_id", mid)
                update_cache("toss_notified", False)
                update_cache("result_notified", False)
                update_cache("live_scorecard", None)
                update_cache("live_innings", None)

                print(f"🏏 {match['team1']} vs {match['team2']}")

                toss = match.get("toss", "")
                if toss:
                    broadcast(
                        f"🪙 <b>TOSS!</b>\n\n"
                        f"<b>{match['team1']}</b> vs "
                        f"<b>{match['team2']}</b>\n\n"
                        f"{toss}\n\n"
                        f"Match starting soon! 🏏"
                    )
                    update_cache("toss_notified", True)
                else:
                    broadcast(
                        f"🏏 <b>MATCH ALERT!</b>\n\n"
                        f"<b>{match['team1']}</b> vs "
                        f"<b>{match['team2']}</b>\n\n"
                        f"Watching for THRILLS! 👀"
                    )

            # Toss late mila
            elif not cache["toss_notified"] and match.get("toss"):
                broadcast(
                    f"🪙 <b>TOSS!</b>\n\n"
                    f"{match['toss']}\n\n"
                    f"Match is ON! 🏏"
                )
                update_cache("toss_notified", True)

            # ─── SCORECARD - 1 API call ───
            scard = fetch_scorecard(mid)

            if not scard:
                time.sleep(900)
                continue

            # ─── MATCH RESULT ───
            status = (scard.get("status", "") or "").lower()
            is_done = (
                "won" in status or
                "tie" in status or
                "no result" in status or
                "abandoned" in status
            )

            if is_done and not cache["result_notified"]:
                thrill = calculate_thrill_score(scard)
                bar = "🔥" * thrill + "⬜" * (10 - thrill)

                scores = []
                for inn in scard.get("score", []):
                    n = inn.get("inning", "")
                    r = inn.get("r", 0)
                    w = inn.get("w", 0)
                    o = inn.get("o", 0)
                    if n:
                        scores.append(f"  {n}: {r}/{w} ({o} ov)")

                if thrill >= 8:
                    comment = "🔴 WHAT A MATCH!"
                elif thrill >= 6:
                    comment = "🏏 Good contest!"
                elif thrill >= 4:
                    comment = "😊 Decent game."
                else:
                    comment = "😴 One-sided."

                broadcast(
                    f"🏆 <b>MATCH RESULT</b>\n\n"
                    f"{scard.get('status', 'Match Over')}\n\n"
                    f"📊 <b>Scorecard:</b>\n"
                    f"{chr(10).join(scores)}\n\n"
                    f"🔥 <b>THRILL RATING: {thrill}/10</b>\n"
                    f"{bar}\n\n"
                    f"{comment}"
                )

                update_cache("result_notified", True)
                update_cache("current_match_id", None)
                update_cache("live_match", None)
                update_cache("live_scorecard", None)
                update_cache("live_innings", None)

                print(f"🏆 Result sent. Thrill: {thrill}/10")
                time.sleep(3600)
                continue

            # ─── THRILL DETECTION ───
            data = parse_current_innings(scard)

            if data:
                alerts = detect_thrills(mid, data)
                for a in alerts:
                    print(f"🎯 {a['type']}")
                    broadcast(a["message"])

                # ─── POLLING SPEED ───
                overs = data["overs"]
                wickets = data["wickets"]
                innings_id = data["innings_id"]
                target = data.get("target")
                req_rate = data.get("req_rate", 0)

                if innings_id >= 2 and target:
                    runs_needed = target - data["runs"]

                    if overs >= 17.0 and 0 < runs_needed <= 30:
                        wait = 120   # 2 min
                        print("🔥 Nail biter - 2 min")

                    elif overs >= 15.0 and 0 < runs_needed <= 60:
                        wait = 300   # 5 min
                        print("🔴 Thriller - 5 min")

                    elif req_rate >= 14.0 and overs >= 10.0:
                        wait = 480   # 8 min
                        print("📈 Steep - 8 min")

                    else:
                        wait = 900   # 15 min
                        print("🏏 Chase - 15 min")

                else:
                    if wickets >= 5 and overs <= 15:
                        wait = 480   # 8 min
                        print("😱 Collapse - 8 min")

                    elif overs >= 16.0:
                        wait = 480   # 8 min
                        print("💥 Death - 8 min")

                    else:
                        wait = 1500  # 25 min
                        print("😎 Normal - 25 min")
            else:
                wait = 600
                print("⏸️ Break - 10 min")

            time.sleep(wait)

        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(600)


# ─────────────────────────────────────────
# START
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("🏏 Thrill Alert Bot Starting...")

    threading.Thread(target=run_server, daemon=True).start()

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

    threading.Thread(
        target=smart_poll_loop,
        daemon=True
    ).start()
    print("✅ Polling started")

    bot.polling(none_stop=True, timeout=30, interval=1)
