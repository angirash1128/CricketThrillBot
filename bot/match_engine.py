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

# Cache dictionary
cache = {
    "match_id": None,
    "t1": "",
    "t2": "",
    "t1s": "",
    "t2s": "",
    "status": "",
    "tpiw": "",
    "score": [],
    "match_active": False,
    "last_updated": None,
}

# Notification state (track what we've already sent)
notif_state = {
    "match_started": False,
    "toss_sent": False,
    "wicket_collapse_1st": False,
    "trouble_1st": False,
    "thriller_sent": False,
    "nail_biter_sent": False,
    "tough_chase_sent": False,
    "result_sent": False,
    "last_wickets": 0,
}

# Bot reference
_bot = None
_alert_users = None


def set_bot(bot, alert_users):
    global _bot, _alert_users
    _bot = bot
    _alert_users = alert_users


def send_alert(message):
    """Send notification to all subscribed users"""
    if not _bot or not _alert_users:
        return
    for uid in list(_alert_users):
        try:
            _bot.send_message(uid, message, parse_mode="Markdown")
        except:
            pass


# ============ API CALLS ============

def fetch_live_scores():
    """Call /cricScore to get all live matches"""
    try:
        r = requests.get(
            f"{BASE_URL}/cricScore",
            params={"apikey": CRICAPI_KEY},
            timeout=10
        )
        data = r.json()
        if data.get("status") == "success":
            return data.get("data", [])
    except Exception as e:
        print(f"[API Error] cricScore: {e}")
    return []


def fetch_match_info(match_id):
    """Call /match_info for detailed score data"""
    try:
        r = requests.get(
            f"{BASE_URL}/match_info",
            params={"apikey": CRICAPI_KEY, "id": match_id},
            timeout=10
        )
        data = r.json()
        if data.get("status") == "success":
            return data.get("data", {})
    except Exception as e:
        print(f"[API Error] match_info: {e}")
    return {}


def find_ipl_match(matches_list):
    """Find active IPL match from list"""
    for m in matches_list:
        series = m.get("series", "")
        ms = m.get("ms", "")
        if "Indian Premier League" in series:
            if ms in ["live", "in progress", "innings break", "toss"]:
                return m
    return None


# ============ SCORE PARSING ============

def parse_score_string(score_str):
    """Parse '123/4 (15.2 Ov)' format"""
    if not score_str:
        return (0, 0, 0.0)
    match = re.match(r'(\d+)/(\d+)\s*\(([0-9.]+)\s*Ov\)', str(score_str).strip())
    if match:
        return (int(match.group(1)), int(match.group(2)), float(match.group(3)))
    return (0, 0, 0.0)


def get_innings_stats(score_list):
    """Extract stats from score[] array. Returns (innings_num, runs, wickets, overs, target)"""
    if not score_list:
        return (1, 0, 0, 0.0, 0)
    
    if len(score_list) == 1:
        s = score_list[0]
        return (1, s.get("r", 0), s.get("w", 0), s.get("o", 0.0), 0)
    
    # 2nd innings
    target = score_list[0].get("r", 0) + 1
    s2 = score_list[1]
    return (2, s2.get("r", 0), s2.get("w", 0), s2.get("o", 0.0), target)


def calc_required_rate(runs_needed, overs):
    """Calculate required run rate for 2nd innings"""
    overs_left = max(0, 20.0 - overs)
    if overs_left <= 0:
        return 99.9
    return round((runs_needed / overs_left) * 1, 2)


# ============ NOTIFICATIONS ============

def check_and_send_notifications():
    """Check all notification conditions"""
    global notif_state
    
    t1 = cache.get("t1", "Team1")
    t2 = cache.get("t2", "Team2")
    t1s = cache.get("t1s", "")
    t2s = cache.get("t2s", "")
    status = cache.get("status", "")
    tpiw = cache.get("tpiw", "")
    score_list = cache.get("score", [])
    
    # 1. MATCH STARTED
    if cache["match_active"] and not notif_state["match_started"]:
        notif_state["match_started"] = True
        msg = f"🏏 *Match Starting!*\n{t1} vs {t2}\n_Monitoring started! 🚨_"
        send_alert(msg)
    
    # 2. TOSS UPDATE
    if tpiw and not notif_state["toss_sent"]:
        notif_state["toss_sent"] = True
        msg = f"🪙 *Toss Update*\n{tpiw}\n_Match starts soon!_"
        send_alert(msg)
    
    if not score_list:
        return
    
    innings_num, runs, wickets, overs, target = get_innings_stats(score_list)
    
    # 3. WICKET COLLAPSE
    if wickets - notif_state["last_wickets"] >= 2:
        msg = f"💥 *Wicket Collapse!*\n{t1} vs {t2}\n{wickets - notif_state['last_wickets']} wickets fell!\n{t1s if innings_num == 1 else t2s}"
        send_alert(msg)
    
    notif_state["last_wickets"] = wickets
    
    # 4. TEAM IN TROUBLE (1st innings only)
    if innings_num == 1 and not notif_state["trouble_1st"]:
        if overs >= 5 and wickets >= 6:
            ipl_avg = overs * 8.5 * 0.75
            if runs < ipl_avg:
                notif_state["trouble_1st"] = True
                msg = f"😬 *Team in Trouble!*\n{t1}\n{runs}/{wickets} in {overs} overs\n_Well below IPL average_"
                send_alert(msg)
    
    # 2nd innings checks
    if innings_num == 2 and target > 0:
        runs_needed = target - runs
        rr = calc_required_rate(runs_needed, overs)
        
        # 5. THRILLER
        if not notif_state["thriller_sent"] and overs >= 15.0 and runs_needed <= 60:
            notif_state["thriller_sent"] = True
            msg = f"🔥 *Thriller!*\n{t1} vs {t2}\nNeed {runs_needed} in {20-int(overs)} overs!\nRRR: {rr}"
            send_alert(msg)
        
        # 6. NAIL BITER
        if not notif_state["nail_biter_sent"] and overs >= 17.0 and runs_needed <= 30:
            notif_state["nail_biter_sent"] = True
            msg = f"😱 *NAIL BITER!*\n{t1} vs {t2}\nNeed {runs_needed} runs!\nRRR: {rr}\n_EDGE OF SEAT STUFF!_"
            send_alert(msg)
        
        # 7. TOUGH CHASE
        if not notif_state["tough_chase_sent"] and overs >= 10.0 and rr >= 14.0:
            notif_state["tough_chase_sent"] = True
            msg = f"🏔️ *Tough Chase!*\n{t1} vs {t2}\nNeed {runs_needed}, RRR: {rr}"
            send_alert(msg)
    
    # 8. MATCH RESULT
    if not notif_state["result_sent"]:
        status_lower = status.lower()
        if any(word in status_lower for word in ["won", "tie", "no result"]):
            notif_state["result_sent"] = True
            thrill = calc_thrill_rating(score_list, status_lower)
            stars = "⭐" * thrill
            
            score_text = ""
            for s in score_list:
                r, w, o = s.get("r", 0), s.get("w", 0), s.get("o", 0.0)
                score_text += f"\n  {s.get('inning', 'Innings')}: {r}/{w} ({o} ov)"
            
            msg = f"🏆 *Match Result*\n{t1} vs {t2}\n{status}{score_text}\n\n*Thrill Rating: {thrill}/10*\n{stars}"
            send_alert(msg)


def calc_thrill_rating(score_list, status_lower):
    """Calculate thrill rating 1-10"""
    rating = 3
    
    if "super over" in status_lower or "tie" in status_lower:
        return 10
    
    if "1 wicket" in status_lower or "1 run" in status_lower:
        rating += 4
    elif "2 wicket" in status_lower or "2 run" in status_lower:
        rating += 3
    elif "3 wicket" in status_lower or "3 run" in status_lower:
        rating += 2
    
    if score_list and score_list[0].get("r", 0) >= 220:
        rating += 2
    elif score_list and score_list[0].get("r", 0) >= 190:
        rating += 1
    
    if score_list and len(score_list) >= 2 and score_list[1].get("o", 0.0) >= 19.0:
        rating += 1
    
    return min(10, rating)


# ============ SMART POLLING ============

def get_poll_interval():
    """Return sleep time in seconds based on match state"""
    if not cache["match_active"]:
        return 900
    
    score_list = cache.get("score", [])
    if not score_list:
        return 900
    
    innings_num, runs, wickets, overs, target = get_innings_stats(score_list)
    
    if innings_num == 1:
        if overs >= 16.0:
            return 480  # 8 min - death overs
        return 1500  # 25 min - normal
    else:
        if target > 0:
            runs_needed = target - runs
            if overs >= 17.0 and runs_needed <= 30:
                return 120  # 2 min - nail biter
            elif overs >= 15.0 and runs_needed <= 60:
                return 300  # 5 min - thriller
        return 900  # 15 min - normal 2nd


def reset_notif_state():
    """Reset when new match starts"""
    global notif_state
    notif_state = {
        "match_started": False,
        "toss_sent": False,
        "wicket_collapse_1st": False,
        "trouble_1st": False,
        "thriller_sent": False,
        "nail_biter_sent": False,
        "tough_chase_sent": False,
        "result_sent": False,
        "last_wickets": 0,
    }


# ============ POLL LOOP ============

def poll_loop():
    """Main background polling thread"""
    print("[Poll] Started")
    last_match_id = None
    
    while True:
        try:
            # Sleep during non-match hours
            if not is_match_window_open():
                time.sleep(600)
                continue
            
            # Fetch live matches
            live_matches = fetch_live_scores()
            ipl_match = find_ipl_match(live_matches)
            
            if ipl_match:
                match_id = ipl_match.get("id")
                
                # New match detected
                if match_id != last_match_id:
                    reset_notif_state()
                    last_match_id = match_id
                
                # Update cache from cricScore
                cache["match_id"] = match_id
                cache["t1"] = ipl_match.get("t1", "")
                cache["t2"] = ipl_match.get("t2", "")
                cache["t1s"] = ipl_match.get("t1s", "")
                cache["t2s"] = ipl_match.get("t2s", "")
                cache["status"] = ipl_match.get("status", "")
                cache["tpiw"] = ipl_match.get("tpiw", "")
                cache["match_active"] = True
                cache["last_updated"] = datetime.now(IST).strftime("%H:%M:%S IST")
                
                # Fetch detailed info for score[]
                match_info = fetch_match_info(match_id)
                if match_info:
                    cache["score"] = match_info.get("score", [])
                    if match_info.get("status"):
                        cache["status"] = match_info.get("status")
                
                # Check notifications
                check_and_send_notifications()
                
                # Check if match over
                if any(word in cache["status"].lower() for word in ["won", "tie", "no result"]):
                    cache["match_active"] = False
                    time.sleep(3600)
                    continue
            else:
                cache["match_active"] = False
            
            # Sleep with smart interval
            interval = get_poll_interval()
            time.sleep(interval)
            
        except Exception as e:
            print(f"[Poll Error] {e}")
            time.sleep(300)


def start_poll_thread():
    """Start polling in background"""
    t = threading.Thread(target=poll_loop, daemon=True)
    t.start()


# ============ CACHE DISPLAY ============

def get_live_match_message():
    """Format live match info from cache"""
    if not cache["match_active"] or not cache["t1"]:
        return "🏏 No IPL match currently live.\n\n_Check back during match time!_"
    
    t1, t2 = cache.get("t1", "?"), cache.get("t2", "?")
    t1s, t2s = cache.get("t1s", "-"), cache.get("t2s", "-")
    status = cache.get("status", "-")
    tpiw = cache.get("tpiw", "")
    score_list = cache.get("score", [])
    last_upd = cache.get("last_updated", "N/A")
    
    lines = [f"🏏 *{t1} vs {t2}*"]
    
    if tpiw:
        lines.append(f"🪙 {tpiw}")
    
    lines.append("")
    
    if score_list:
        for s in score_list:
            r, w, o = s.get("r", 0), s.get("w", 0), s.get("o", 0.0)
            if o > 0:
                crr = round(r / o, 2)
                lines.append(f"📊 {s.get('inning', 'Innings')}: *{r}/{w}* ({o} ov) | CRR: {crr}")
            else:
                lines.append(f"📊 {s.get('inning', 'Innings')}: *{r}/{w}* ({o} ov)")
        
        innings_num, runs, wickets, overs, target = get_innings_stats(score_list)
        if innings_num == 2 and target > 0:
            needed = target - runs
            rr = calc_required_rate(needed, overs)
            lines.append(f"🎯 Need: {needed} in {20-int(overs)} ov | RRR: {rr}")
    else:
        if t1s:
            lines.append(f"🏏 {t1}: {t1s}")
        if t2s:
            lines.append(f"🏏 {t2}: {t2s}")
    
    lines.append(f"\n📍 *{status}*")
    lines.append(f"\n_Updated: {last_upd}_")
    
    return "\n".join(lines)


def get_debug_info():
    """Cache info for /debug command"""
    return (
        f"🔧 *Debug Cache*\n"
        f"ID: {cache.get('match_id', 'None')}\n"
        f"Active: {cache.get('match_active', False)}\n"
        f"{cache.get('t1', '?')} vs {cache.get('t2', '?')}\n"
        f"Status: {cache.get('status', '-')}\n"
        f"Updated: {cache.get('last_updated', 'Never')}"
    )
