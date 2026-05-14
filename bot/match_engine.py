import os, time, requests, threading, pytz
from datetime import datetime
import ipl_schedule

CRICAPI_KEY = os.environ.get("CRICAPI_KEY", "")
BASE_URL = "https://api.cricapi.com/v1"
IST = pytz.timezone("Asia/Kolkata")

cache = {"live_match": None, "full_schedule": [], "last_api_call": 0, "match_active": False, "prev_status": ""}
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

def check_for_alerts(current_match):
    global cache, _bot, _alert_users
    if not current_match or not _bot: return
    
    new_status = current_match.get("status", "").lower()
    old_status = cache["prev_status"].lower()
    
    # Alert Logic: Rain Stop, Super Over, or Match Restart
    alert_msg = ""
    if "super over" in new_status:
        alert_msg = f"🚨 *SUPER OVER ALERT!* 🚨\n\nMatch tie ho gaya hai! Super Over shuru ho raha hai! 🔥"
    elif ("rain" not in new_status and "rain" in old_status) or ("starts" in new_status and "delayed" in old_status):
        alert_msg = f"⚡ *GAME ON!* ⚡\n\nBaarish ruk gayi hai ya match dobara shuru ho raha hai! Don't miss the thrill!"
    
    if alert_msg and _alert_users:
        for user_id in _alert_users:
            try: _bot.send_message(user_id, alert_msg, parse_mode="Markdown")
            except: pass
    
    cache["prev_status"] = new_status

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

def get_debug_info():
    return f"🔧 *Bot Status*\nLive: {cache['match_active']}\nLast Update: {time.strftime('%H:%M', time.localtime(cache['last_api_call']))}"
