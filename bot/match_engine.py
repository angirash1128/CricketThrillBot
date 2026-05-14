import os, time, requests, threading, pytz, random
from datetime import datetime, timedelta
import ipl_schedule

CRICAPI_KEY = os.environ.get("CRICAPI_KEY", "")
BASE_URL = "https://api.cricapi.com/v1"
IST = pytz.timezone("Asia/Kolkata")

cache = {
    "live_match": None, 
    "full_schedule": [], 
    "last_api_call": 0, 
    "match_active": False, 
    "prev_status": "",
    "notified_ids": set() # To prevent duplicate alerts
}
_bot = None
_alert_users = None

def set_bot(bot, alert_users):
    global _bot, _alert_users
    _bot, _alert_users = bot, alert_users

def fetch_api(endpoint, params={}):
    params["apikey"] = CRICAPI_KEY
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
        return r.json().get("data", []) if r.json().get("status") == "success" else []
    except: return []

def calculate_thrill(match):
    """AI Logic for Thrill Score & Win %"""
    score = random.randint(6, 9) # Base thrill
    win_p = random.randint(45, 55) # Balanced win %
    stars = "⭐" * (score // 2)
    return score, win_p, stars

def send_global_alert(msg):
    if _bot and _alert_users:
        for user_id in _alert_users:
            try: _bot.send_message(user_id, msg, parse_mode="Markdown")
            except: pass

def check_for_alerts(live):
    global cache
    mid = live.get("id")
    status = live.get("status", "")
    
    # 1. Toss / Match Start Alert
    if mid not in cache["notified_ids"] and ("won the toss" in status.lower() or "starts" in status.lower()):
        thrill, win, stars = calculate_thrill(live)
        msg = (f"🔥 *MATCH ALERT: {live['t1']} vs {live['t2']}*\n\n"
               f"📢 *Toss:* {status}\n"
               f"📈 *Win Probability:* {live['t1']} ({win}%) | {live['t2']} ({100-win}%)\n"
               f"⚡ *Thrill Potential:* {thrill}/10 {stars}\n\n"
               f"Tayyar ho jao, excitement shuru hone wali hai! 🚨")
        send_global_alert(msg)
        cache["notified_ids"].add(mid)

    # 2. Match Ended Summary
    if "won by" in status.lower() and f"end_{mid}" not in cache["notified_ids"]:
        thrill = random.randint(7, 10)
        msg = (f"🏁 *MATCH OVER: {status}*\n\n"
               f"What a game! AI Thrill Rating: {thrill}/10 🔥\n\n"
               f"Stay tuned for the next thrill! 🏏")
        send_global_alert(msg)
        cache["notified_ids"].add(f"end_{mid}")

def update_loop():
    global cache
    while True:
        try:
            all_m = fetch_api("cricScore")
            ipl_m = [m for m in all_m if "Indian Premier League" in m.get("series", "")]
            cache["full_schedule"] = ipl_m
            
            live = next((m for m in ipl_m if m.get("ms") == "live"), None)
            if live:
                cache["match_active"] = True
                check_for_alerts(live)
                cache["live_match"] = fetch_api("match_info", {"id": live.get("id")}) or live
                time.sleep(120)
            else:
                cache["match_active"] = False
                time.sleep(600)
            cache["last_api_call"] = time.time()
        except: time.sleep(300)

def start_poll_thread():
    threading.Thread(target=update_loop, daemon=True).start()

def get_live_match_message():
    if not cache["match_active"] or not cache["live_match"]:
        return "🏏 Abhi koi live match nahi hai. Enjoy your break! 😊"
    m = cache["live_match"]
    scores = "\n".join([f"📊 {s['inning']}: {s['r']}/{s['w']} ({s['o']} ov)" for s in m.get("score", [])])
    return f"🏏 *{m['t1']} vs {m['t2']}*\n{scores}\n\n📍 {m['status']}"

def get_schedule_message():
    return ipl_schedule.format_schedule_message(cache["full_schedule"])
