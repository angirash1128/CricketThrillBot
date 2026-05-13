import os
import time
import requests
import threading
import re
from datetime import datetime
import pytz

from ipl_schedule import is_match_window_open

CRICAPI_KEY = os.environ.get("CRICAPI_KEY", "")
BASE_URL = "https://api.cricapi.com/v1"
IST = pytz.timezone("Asia/Kolkata")

cache = {
    "match_id": None,
    "t1": "", "t2": "", "t1s": "", "t2s": "",
    "status": "", "tpiw": "", "score": [],
    "match_active": False, "last_updated": None,
}

notif_state = {
    "match_started": False, "toss_sent": False,
    "thriller_sent": False, "nail_biter_sent": False,
    "tough_chase_sent": False, "result_sent": False,
    "last_wickets": 0, "last_thrill_over": 0
}

_bot = None
_alert_users = None

def set_bot(bot, alert_users):
    global _bot, _alert_users
    _bot = bot
    _alert_users = alert_users

def send_alert(message):
    if not _bot or not _alert_users: return
    for uid in list(_alert_users):
        try: _bot.send_message(uid, message, parse_mode="Markdown")
        except: pass

# ============ API CALLS ============

def fetch_live_scores():
    try:
        r = requests.get(f"{BASE_URL}/cricScore", params={"apikey": CRICAPI_KEY}, timeout=10)
        data = r.json()
        return data.get("data", []) if data.get("status") == "success" else []
    except: return []

def fetch_match_info(match_id):
    try:
        r = requests.get(f"{BASE_URL}/match_info", params={"apikey": CRICAPI_KEY, "id": match_id}, timeout=10)
        data = r.json()
        return data.get("data", {}) if data.get("status") == "success" else {}
    except: return {}

def find_ipl_match(matches_list):
    for m in matches_list:
        if "Indian Premier League" in m.get("series", ""):
            if m.get("ms") in ["live", "in progress", "innings break", "toss"]:
                return m
    return None

# ============ LOGIC & POLLING ============

def get_innings_stats(score_list):
    if not score_list: return (1, 0, 0, 0.0, 0)
    if len(score_list) == 1:
        s = score_list[0]
        return (1, s.get("r", 0), s.get("w", 0), s.get("o", 0.0), 0)
    target = score_list[0].get("r", 0) + 1
    s2 = score_list[1]
    return (2, s2.get("r", 0), s2.get("w", 0), s2.get("o", 0.0), target)

def calc_required_rate(runs_needed, overs):
    overs_left = max(0.1, 20.0 - overs)
    return round((runs_needed / overs_left), 2)

def check_and_send_notifications():
    global notif_state
    score_list = cache.get("score", [])
    if not score_list: return

    inn, runs, wickets, overs, target = get_innings_stats(score_list)
    
    # THRILL LOGIC - SIRF TAB JAB MATCH TIGHT HO
    if inn == 2 and target > 0:
        runs_needed = target - runs
        rr = calc_required_rate(runs_needed, overs)
        
        # 1. THRILLER (15th over ke baad, runs needed under 45)
        if not notif_state["thriller_sent"] and overs >= 15.0 and runs_needed <= 45:
            notif_state["thriller_sent"] = True
            send_alert(f"🔥 *THRILLER DETECTED!*\n{cache['t1']} vs {cache['t2']}\nNeed {runs_needed} in {round(20-overs,1)} overs!\nRRR: {rr} 🚨")

        # 2. NAIL BITER (Last 2 overs, match tight)
        if not notif_state["nail_biter_sent"] and overs >= 18.0 and runs_needed <= 20:
            notif_state["nail_biter_sent"] = True
            send_alert(f"😱 *NAIL BITER! MATCH ON THE LINE!*\nNeed {runs_needed} in {round(20-overs,1)} overs!\nDon't miss this! 📺")

    # RESULT
    if not notif_state["result_sent"] and any(w in cache["status"].lower() for w in ["won", "tie", "result"]):
        notif_state["result_sent"] = True
        send_alert(f"🏆 *Match Result*\n{cache['status']}\n\nHope you didn't miss the thrill! 😉")

def get_poll_interval():
    # API SAVING LOGIC
    if not cache["match_active"]: return 900 # 15 min
    
    score_list = cache.get("score", [])
    if not score_list: return 600 # 10 min
    
    inn, runs, wickets, overs, target = get_innings_stats(score_list)
    
    if inn == 1:
        if overs > 18.0: return 300 # 5 min (End of innings)
        return 1200 # 20 min (Boring 1st innings)
    else:
        runs_needed = target - runs
        if overs >= 17.0 and runs_needed <= 30: return 90 # 1.5 min (CRITICAL)
        if overs >= 15.0: return 240 # 4 min (Exciting)
        return 600 # 10 min (Normal chase)

def poll_loop():
    last_match_id = None
    while True:
        try:
            if not is_match_window_open():
                time.sleep(900); continue
            
            live_matches = fetch_live_scores()
            ipl = find_ipl_match(live_matches)
            
            if ipl:
                mid = ipl.get("id")
                if mid != last_match_id:
                    notif_state.update({"thriller_sent":False, "nail_biter_sent":False, "result_sent":False})
                    last_match_id = mid
                
                cache.update({"t1":ipl.get("t1"), "t2":ipl.get("t2"), "status":ipl.get("status"), "match_active":True})
                info = fetch_match_info(mid)
                if info:
                    cache["score"] = info.get("score", [])
                    cache["status"] = info.get("status", cache["status"])
                
                check_and_send_notifications()
                time.sleep(get_poll_interval())
            else:
                cache["match_active"] = False
                time.sleep(600)
        except: time.sleep(300)

def start_poll_thread():
    threading.Thread(target=poll_loop, daemon=True).start()

def get_live_match_message():
    if not cache["match_active"]: return "🏏 No live IPL match for now."
    return f"🏏 *{cache['t1']} vs {cache['t2']}*\n📍 {cache['status']}\n\n_Alerts will be sent for thrill moments!_"

def get_debug_info():
    return f"Status: {cache['status']}\nActive: {cache['match_active']}"
