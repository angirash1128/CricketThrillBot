import os, time, requests, threading, pytz, random
from datetime import datetime
import ipl_schedule

CRICAPI_KEY = os.environ.get("CRICAPI_KEY", "")
BASE_URL = "https://api.cricapi.com/v1"
IST = pytz.timezone("Asia/Kolkata")

cache = {
    "live_match": None, 
    "full_schedule": [], 
    "last_api_call": 0, 
    "match_active": False, 
    "notified_ids": set(),
    "api_count_today": 0
}
_bot = None
_alert_users = None

def set_bot(bot, alert_users):
    global _bot, _alert_users
    _bot, _alert_users = bot, alert_users

def fetch_api(endpoint, params={}):
    global cache
    if cache["api_count_today"] >= 98: return []
    params["apikey"] = CRICAPI_KEY
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
        cache["api_count_today"] += 1
        return r.json().get("data", []) if r.json().get("status") == "success" else []
    except: return []

def send_global_alert(msg):
    if _bot and _alert_users:
        for user_id in list(_alert_users):
            try: _bot.send_message(user_id, msg, parse_mode="Markdown")
            except: pass

def check_for_alerts(live):
    global cache
    mid = live.get("id")
    status = live.get("status", "").lower()
    if mid not in cache["notified_ids"] and ("won the toss" in status or "starts" in status):
        msg = f"🔥 *MATCH ALERT: {live['t1']} vs {live['t2']}*\n\n📢 {status.capitalize()}\n⚡ Thrill Potential: 8/10 ⭐⭐⭐⭐"
        send_global_alert(msg)
        cache["notified_ids"].add(mid)

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
                wait_time = 300 # 5 min wait
            else:
                cache["match_active"] = False
                wait_time = 900 # 15 min wait
            time.sleep(wait_time)
        except: time.sleep(300)

def start_poll_thread():
    threading.Thread(target=update_loop, daemon=True).start()

def get_live_match_message():
    if not cache.get("match_active"): return "🏏 Abhi koi live match nahi hai."
    m = cache.get("live_match", {})
    return f"🏏 *{m.get('t1')} vs {m.get('t2')}*\n📍 {m.get('status')}"

def get_schedule_message():
    return ipl_schedule.format_schedule_message(cache["full_schedule"])
