import os
import time
import requests
import threading
import pytz
from datetime import datetime
import ipl_schedule

CRICAPI_KEY = os.environ.get("CRICAPI_KEY", "")
BASE_URL = "https://api.cricapi.com/v1"
IST = pytz.timezone("Asia/Kolkata")

# Centralized Memory (Cache)
cache = {
    "live_match": None,
    "full_schedule": [],
    "last_api_call": 0,
    "match_active": False
}

_bot = None
_alert_users = None

def set_bot(bot, alert_users):
    global _bot, _alert_users
    _bot = bot
    _alert_users = alert_users

def fetch_api(endpoint, params={}):
    params["apikey"] = CRICAPI_KEY
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
        data = r.json()
        return data.get("data", []) if data.get("status") == "success" else []
    except: return []

def update_loop():
    """Ye loop background mein auto-pilot par chalta rahega"""
    global cache
    while True:
        try:
            # 1. Fetch Schedule (Auto-updates for any series/IPL)
            all_matches = fetch_api("cricScore")
            # Sabhi major matches ko filter kar rahe hain
            ipl_matches = [m for m in all_matches if "Indian Premier League" in m.get("series", "")]
            cache["full_schedule"] = ipl_matches
            
            # 2. Check for Live Match
            live = next((m for m in ipl_matches if m.get("ms") == "live"), None)
            
            if live:
                cache["match_active"] = True
                detail = fetch_api("match_info", {"id": live.get("id")})
                cache["live_match"] = detail if detail else live
                wait_time = 120 # Live match: 2 min refresh
            else:
                cache["match_active"] = False
                cache["live_match"] = None
                wait_time = 900 # Normal: 15 min refresh

            cache["last_api_call"] = time.time()
            time.sleep(wait_time)
        except: time.sleep(300)

def start_poll_thread():
    threading.Thread(target=update_loop, daemon=True).start()

def get_live_match_message():
    if not cache["match_active"] or not cache["live_match"]:
        return "🏏 Abhi koi IPL match live nahi hai.\n\nSchedule ke liye niche button dabayein."
    
    m = cache["live_match"]
    score_lines = []
    if "score" in m:
        for s in m["score"]:
            score_lines.append(f"📊 {s.get('inning')}: {s.get('r')}/{s.get('w')} ({s.get('o')} ov)")
    
    return f"🏏 *{m.get('t1')} vs {m.get('t2')}*\n" + "\n".join(score_lines) + f"\n\n📍 {m.get('status')}"

def get_schedule_message():
    return ipl_schedule.format_schedule_message(cache["full_schedule"])

def get_debug_info():
    """Bot ki health check karne ke liye function"""
    last_call = time.strftime('%H:%M:%S', time.localtime(cache["last_api_call"]))
    return (
        f"🔧 *Debug Stats*\n"
        f"Active Match: {cache['match_active']}\n"
        f"Last API Update: {last_call} IST\n"
        f"Matches in Cache: {len(cache['full_schedule'])}"
    )
