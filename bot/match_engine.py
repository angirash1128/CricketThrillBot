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

# Bot ki memory (Auto-update hogi)
cache = {
    "live_match": None,      # Current live match ka data
    "full_schedule": [],     # Saare IPL matches ki list
    "last_api_call": 0,      # API kab call hui thi
    "match_active": False
}

_bot = None
_alert_users = None

def set_bot(bot, alert_users):
    global _bot, _alert_users
    _bot = bot
    _alert_users = alert_users

def fetch_data_from_api(endpoint, params={}):
    """API se data lane ka common function"""
    params["apikey"] = CRICAPI_KEY
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
        data = r.json()
        return data.get("data", []) if data.get("status") == "success" else []
    except:
        return []

def update_engine():
    """Ye function har thodi der mein khud chalega aur data refresh karega"""
    global cache
    while True:
        try:
            print("[Engine] Refreshing data...")
            
            # 1. Sabse pehle saare matches (Schedule) le aao
            # 'cricScore' endpoint se saare live matches milte hain
            all_matches = fetch_data_from_api("cricScore")
            
            # Sirf IPL matches filter karna
            ipl_matches = [m for m in all_matches if "Indian Premier League" in m.get("series", "")]
            cache["full_schedule"] = ipl_matches
            
            # 2. Check karo koi match LIVE hai kya?
            live = next((m for m in ipl_matches if m.get("ms") == "live"), None)
            
            if live:
                cache["match_active"] = True
                # Live match ki detail fetch karo
                detail = fetch_data_from_api("match_info", {"id": live.get("id")})
                cache["live_match"] = detail if detail else live
            else:
                cache["match_active"] = False
                cache["live_match"] = None

            cache["last_api_call"] = time.time()
            
            # Sleep timing: Agar match live hai to 2 min, warna 15 min
            sleep_time = 120 if cache["match_active"] else 900
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"Engine Error: {e}")
            time.sleep(300)

def start_poll_thread():
    """Engine ko background mein start karta hai"""
    t = threading.Thread(target=update_engine, daemon=True)
    t.start()

def get_live_match_message():
    """User ko cache se data dikhata hai (No API call here)"""
    if not cache["match_active"] or not cache["live_match"]:
        return "🏏 Abhi koi IPL match live nahi hai.\n\nSchedule check karne ke liye button dabayein."
    
    m = cache["live_match"]
    t1, t2 = m.get("t1"), m.get("t2")
    status = m.get("status", "")
    
    # Score nikalna (Agar detailed data hai)
    score_text = ""
    if "score" in m and m["score"]:
        for s in m["score"]:
            score_text += f"\n📊 {s.get('inning')}: {s.get('r')}/{s.get('w')} ({s.get('o')} ov)"
            
    return f"🏏 *{t1} vs {t2}*\n{score_text}\n\n📍 {status}"

def get_schedule_message():
    """ipl_schedule file ko data bhejta hai formatting ke liye"""
    return ipl_schedule.format_schedule_message(cache["full_schedule"])
