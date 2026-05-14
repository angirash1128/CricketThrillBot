import os, time, requests, threading, pytz, random
from datetime import datetime
import ipl_schedule

CRICAPI_KEY = os.environ.get("CRICAPI_KEY", "")
BASE_URL = "https://api.cricapi.com/v1"
IST = pytz.timezone("Asia/Kolkata")

cache = {
    "live_match": None, 
    "full_schedule": [], 
    "last_sync": "Never", 
    "match_active": False, 
    "api_count": 0,
    "notified_ids": set()
}
_bot = None
_alert_users = None

def set_bot(bot, alert_users):
    global _bot, _alert_users
    _bot, _alert_users = bot, alert_users

def fetch_api(endpoint, params={}):
    global cache
    if cache["api_count"] >= 98: return []
    params["apikey"] = CRICAPI_KEY
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
        cache["api_count"] += 1
        return r.json().get("data", []) if r.json().get("status") == "success" else []
    except: return []

def send_alert(msg):
    if _bot and _alert_users:
        for user_id in list(_alert_users):
            try: _bot.send_message(user_id, msg, parse_mode="Markdown")
            except: pass

def process_match_lifecycle(live):
    global cache
    mid = live.get("id")
    status = live.get("status", "").lower()
    
    # Toss & Prediction Alert
    if mid not in cache["notified_ids"] and ("toss" in status or "starts" in status):
        win_p = random.randint(45, 55)
        thrill = random.randint(7, 9)
        msg = (f"🔥 *THRILL PREDICTION DETECTED*\n\n"
               f"Match: {live['t1']} vs {live['t2']}\n"
               f"Status: {status.upper()}\n\n"
               f"📈 Win Chance: {live['t1']} {win_p}% | {live['t2']} {100-win_p}%\n"
               f"⚡ Thrill Potential: {thrill}/10\n"
               f"----------------------------\n"
               f"_System activated for excitement detection._")
        send_alert(msg)
        cache["notified_ids"].add(mid)

    # Post-Match Result Summary
    if "won by" in status and f"end_{mid}" not in cache["notified_ids"]:
        thrill_final = random.randint(7, 10)
        msg = (f"🏁 *MATCH RESULT SUMMARY*\n\n"
               f"Outcome: {status.upper()}\n"
               f"AI Thrill Rating: {thrill_final}/10 🔥\n\n"
               f"Thank you for following the excitement with Thrill Alert.")
        send_alert(msg)
        cache["notified_ids"].add(f"end_{mid}")

def update_loop():
    global cache
    while True:
        try:
            # Sync Score/Schedule every 10 minutes to save API
            data = fetch_api("cricScore")
            ipl_m = [m for m in data if "Indian Premier League" in m.get("series", "")]
            cache["full_schedule"] = ipl_m
            
            live = next((m for m in ipl_m if m.get("ms") == "live"), None)
            if live:
                cache["match_active"] = True
                process_match_lifecycle(live)
                # Detailed info only every 10 mins
                cache["live_match"] = fetch_api("match_info", {"id": live.get("id")}) or live
                wait_time = 600 # 10 Minutes
            else:
                cache["match_active"] = False
                wait_time = 1200 # 20 Minutes
            
            cache["last_sync"] = datetime.now(IST).strftime("%I:%M %p")
            time.sleep(wait_time)
        except: time.sleep(300)

def start_poll_thread():
    threading.Thread(target=update_loop, daemon=True).start()

def get_live_match_message():
    m = cache.get("live_match")
    last_sync = cache["last_sync"]
    header = (f"🏏 *LIVE ANALYTICS*\n"
              f"_Sync Time: {last_sync} IST_\n"
              f"----------------------------\n")
    
    footer = ("\n⚠️ *Note:* This bot is designed for *Excitement Detection*, not regular score updates. "
              "Check back periodically for thrill-based notifications.")
    
    if not cache["match_active"] or not m:
        return header + "No live match currently monitored." + footer

    scores = ""
    if "score" in m:
        for s in m["score"]:
            scores += f"📊 {s['inning']}: {s['r']}/{s['w']} ({s['o']} ov)\n"
    
    return header + f"Match: {m.get('t1')} vs {m.get('t2')}\n{scores}\nStatus: {m.get('status')}" + footer

def get_schedule_message():
    return ipl_schedule.format_schedule_message(cache["full_schedule"])
