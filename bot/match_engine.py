import os
import time
import threading
import pytz
from datetime import datetime, timedelta

import api_manager
import database
import ipl_schedule
import alert_manager
import feedback_sheet
from thrill_calculator import (
    calculate_win_probability,
    calculate_thrill_score,
    detect_probability_swing,
    get_polling_interval,
    get_match_phase
)

IST = pytz.timezone("Asia/Kolkata")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "")

_bot = None

_engine_state = {
    "running": False,
    "current_match_id": None,
    "current_match_data": None,
    "last_t1_prob": None,
    "last_t2_prob": None,
    "last_thrill": None,
    "match_phase": "pre_match",
    "schedule_synced_date": None,
    "today_match": None,
    "last_admin_alert_count": 0
}

_state_lock = threading.Lock()

def set_bot(bot):
    global _bot
    _bot = bot
    database.init_db()
    print("[Engine] Bot reference set, DB initialized.")

def send_to_all_users(message):
    if not _bot:
        return
    users = database.get_all_subscribed_users()
    sent = 0
    for uid in users:
        try:
            _bot.send_message(uid, message, parse_mode="Markdown")
            sent += 1
        except Exception as e:
            print(f"[Send Error] User {uid}: {e}")
    print(f"[Engine] Alert sent to {sent}/{len(users)} users.")

def send_to_admin(message):
    if not _bot or not ADMIN_USER_ID:
        return
    try:
        _bot.send_message(int(ADMIN_USER_ID), message, parse_mode="Markdown")
    except Exception as e:
        print(f"[Admin Send Error] {e}")

def check_api_warning():
    """Notify admin when API hits 70 and 90."""
    count = api_manager.get_api_count()
    last_alert = _engine_state["last_admin_alert_count"]
    
    if count >= 90 and last_alert < 90:
        send_to_admin(alert_manager.admin_alert("⚠️ API limit 90+! Only 5 calls left today.", count))
        _engine_state["last_admin_alert_count"] = 90
    elif count >= 70 and last_alert < 70:
        send_to_admin(alert_manager.admin_alert("📊 API usage at 70+. Monitor carefully.", count))
        _engine_state["last_admin_alert_count"] = 70

def sync_morning_schedule():
    """Run once per day to fetch today's IPL match."""
    today = datetime.now(IST).strftime("%Y-%m-%d")
    if _engine_state["schedule_synced_date"] == today:
        return _engine_state["today_match"]
    
    print(f"[Engine] Morning sync for {today}...")
    all_matches = api_manager.get_today_schedule()
    
    if not all_matches:
        print("[Engine] No matches received from API.")
        return None
    
    today_match = ipl_schedule.get_today_ipl_match(all_matches)
    
    with _state_lock:
        _engine_state["schedule_synced_date"] = today
        _engine_state["today_match"] = today_match
    
    if today_match:
        t1 = today_match.get("t1") or today_match.get("team1") or "?"
        t2 = today_match.get("t2") or today_match.get("team2") or "?"
        dt = today_match.get("_ist_datetime")
        time_str = dt.strftime("%I:%M %p") if dt else "TBD"
        print(f"[Engine] Today's IPL match: {t1} vs {t2} at {time_str}")
        send_to_admin(alert_manager.admin_alert(
            f"📅 Today's match locked: {t1} vs {t2} at {time_str} IST",
            api_manager.get_api_count()
        ))
    else:
        print("[Engine] No IPL match today.")
    
    return today_match

def get_full_match_data(match_id):
    """Fetch detailed match info using match_info endpoint."""
    info = api_manager.get_match_info(match_id)
    if info and isinstance(info, dict):
        return info
    
    all_matches = api_manager.get_today_schedule()
    if all_matches:
        for m in all_matches:
            if m.get("id") == match_id:
                return m
    return None

def detect_and_send_alerts(match_data):
    """Core logic: decide which alert to send based on match state."""
    match_id = match_data.get("id")
    if not match_id:
        return
    
    status = (match_data.get("status") or "").lower()
    score_data = match_data.get("score", [])
    
    t1_prob, t2_prob, prob_source = calculate_win_probability(match_data)
    
    prev_prob = (_engine_state["last_t1_prob"], _engine_state["last_t2_prob"]) if _engine_state["last_t1_prob"] else None
    thrill, reason = calculate_thrill_score(match_data, prev_prob)
    
    swing = detect_probability_swing(t1_prob, _engine_state["last_t1_prob"]) if _engine_state["last_t1_prob"] else 0
    
    database.log_probability(match_id, t1_prob, t2_prob, thrill)
    
    phase = get_match_phase(score_data)
    
    with _state_lock:
        _engine_state["last_t1_prob"] = t1_prob
        _engine_state["last_t2_prob"] = t2_prob
        _engine_state["last_thrill"] = thrill
        _engine_state["match_phase"] = phase
        _engine_state["current_match_data"] = match_data
    
    # 1. Toss Alert
    toss_winner = match_data.get("tossWinner", "")
    if toss_winner and not database.is_alert_sent(match_id, "toss"):
        msg = alert_manager.toss_alert_message(match_data, t1_prob, t2_prob, thrill, reason)
        send_to_all_users(msg)
        database.mark_alert_sent(match_id, "toss")
        print(f"[Alert] Toss sent for {match_id}")
        return
    
    # 2. Match Start Alert
    if score_data and not database.is_alert_sent(match_id, "match_start"):
        msg = alert_manager.match_start_message(match_data, t1_prob, t2_prob, thrill)
        send_to_all_users(msg)
        database.mark_alert_sent(match_id, "match_start")
        print(f"[Alert] Match Start sent for {match_id}")
        return
    
    # 3. Innings Break Alert
    if "innings break" in status or "1st innings over" in status:
        if not database.is_alert_sent(match_id, "innings_break"):
            msg = alert_manager.innings_break_message(match_data, t1_prob, t2_prob, thrill)
            send_to_all_users(msg)
            database.mark_alert_sent(match_id, "innings_break")
            print(f"[Alert] Innings Break sent for {match_id}")
            return
    
    # 4. Super Over Alert
    if "super over" in status and not database.is_alert_sent(match_id, "super_over"):
        msg = alert_manager.super_over_alert(match_data)
        send_to_all_users(msg)
        database.mark_alert_sent(match_id, "super_over")
        print(f"[Alert] Super Over sent for {match_id}")
        return
    
    # 5. Rain Delay Alert
    if any(w in status for w in ["rain", "delay", "stopped", "interrupted"]):
        if not database.is_alert_sent(match_id, "rain_delay"):
            msg = alert_manager.rain_delay_message(match_data, t1_prob, t2_prob, thrill)
            send_to_all_users(msg)
            database.mark_alert_sent(match_id, "rain_delay")
            print(f"[Alert] Rain Delay sent for {match_id}")
            return
    
    # 6. Turning Point Alert (probability swing)
    if swing >= 15 and thrill >= 7.0:
        msg = alert_manager.turning_point_alert(match_data, t1_prob, t2_prob, thrill, reason, swing)
        send_to_all_users(msg)
        print(f"[Alert] Turning Point sent (swing: {swing:.1f}%)")
        return
    
    # 7. Thrill Rising Alert (high thrill in death overs)
    if thrill >= 8.5 and phase == "death":
        alert_key = f"thrill_rising_{int(thrill)}_{phase}"
        if not database.is_alert_sent(match_id, alert_key):
            msg = alert_manager.thrill_rising_alert(match_data, t1_prob, t2_prob, thrill, reason)
            send_to_all_users(msg)
            database.mark_alert_sent(match_id, alert_key)
            print(f"[Alert] Thrill Rising sent (thrill: {thrill})")
            return
    
    # 8. Match Result Alert
    if any(w in status for w in ["won by", "match tied", "no result", "abandoned"]):
        if not database.is_alert_sent(match_id, "result"):
            t1_name = match_data.get("t1") or match_data.get("team1") or "Team A"
            t2_name = match_data.get("t2") or match_data.get("team2") or "Team B"
            
            winner = "Match Tied"
            if "won by" in status:
                winner = status.split("won by")[0].strip().title()
            
            reason_text = _generate_winner_reason(match_data)
            msg = alert_manager.match_result_message(match_data, thrill, reason_text)
            send_to_all_users(msg)
            database.mark_alert_sent(match_id, "result")
            
            database.save_match_result(
                match_id, t1_name, t2_name, winner, thrill, status
            )
            
            try:
                feedback_sheet.log_match_summary(
                    match_id, t1_name, t2_name, winner, thrill, api_manager.get_api_count()
                )
            except Exception as e:
                print(f"[Sheet Log Error] {e}")
            
            send_to_admin(alert_manager.admin_alert(
                f"✅ Match ended: {t1_name} vs {t2_name}\nWinner: {winner}\nThrill: {thrill}/10",
                api_manager.get_api_count()
            ))
            print(f"[Alert] Result sent for {match_id}")
            return

def _generate_winner_reason(match_data):
    score_data = match_data.get("score", [])
    if len(score_data) < 2:
        return "Strong all-round performance."
    
    inn1 = score_data[0]
    inn2 = score_data[1]
    
    try:
        t1_runs = int(inn1.get("r", 0))
        t2_runs = int(inn2.get("r", 0))
        t1_wkts = int(inn1.get("w", 0))
        t2_wkts = int(inn2.get("w", 0))
        
        if t2_runs > t1_runs:
            return f"Successful chase with {10 - t2_wkts} wickets in hand."
        elif t1_runs > t2_runs:
            margin = t1_runs - t2_runs
            return f"Strong defensive bowling, won by {margin} runs."
        else:
            return "Match decided in dramatic fashion."
    except:
        return "Strong all-round performance."

def is_match_finished(match_data):
    status = (match_data.get("status") or "").lower()
    return any(w in status for w in ["won by", "match tied", "no result", "abandoned"])

def engine_loop():
    """Main intelligent polling loop."""
    print("[Engine] Polling loop started.")
    
    while True:
        try:
            check_api_warning()
            
            today_match = sync_morning_schedule()
            
            if not today_match:
                print("[Engine] No IPL match today, sleeping 1 hour...")
                time.sleep(3600)
                continue
            
            match_id = today_match.get("id")
            
            if database.is_alert_sent(match_id, "result"):
                print(f"[Engine] Today's match {match_id} already finished. Sleeping until tomorrow.")
                time.sleep(3600)
                continue
            
            mins_until = ipl_schedule.minutes_until_match(today_match)
            
            if mins_until is not None and mins_until > 30:
                sleep_time = min((mins_until - 25) * 60, 1800)
                print(f"[Engine] Match in {mins_until} mins. Sleeping {sleep_time//60} mins.")
                time.sleep(sleep_time)
                continue
            
            with _state_lock:
                _engine_state["current_match_id"] = match_id
            
            full_data = get_full_match_data(match_id)
            
            if not full_data:
                print("[Engine] No match data fetched. Retrying in 5 mins.")
                time.sleep(300)
                continue
            
            detect_and_send_alerts(full_data)
            
            if is_match_finished(full_data):
                print(f"[Engine] Match {match_id} finished. Stopping polling.")
                time.sleep(3600)
                continue
            
            phase = _engine_state["match_phase"]
            thrill = _engine_state["last_thrill"] or 6.0
            prev_t1 = _engine_state["last_t1_prob"]
            current_t1, _, _ = calculate_win_probability(full_data)
            swing = detect_probability_swing(current_t1, prev_t1) if prev_t1 else 0
            
            interval = get_polling_interval(thrill, phase, swing)
            
            print(f"[Engine] Phase: {phase} | Thrill: {thrill}/10 | Swing: {swing:.1f}% | Next poll in {interval}s")
            time.sleep(interval)
            
        except Exception as e:
            print(f"[Engine Error] {e}")
            time.sleep(300)

def start_poll_thread():
    if _engine_state["running"]:
        print("[Engine] Already running, skip start.")
        return
    _engine_state["running"] = True
    t = threading.Thread(target=engine_loop, daemon=True)
    t.start()
    print("[Engine] Thread started.")

def get_live_match_message():
    """Called when user clicks 'Live Score'."""
    match_data = _engine_state.get("current_match_data")
    
    if not match_data:
        today_match = _engine_state.get("today_match")
        if not today_match:
            return "🏏 *Live Score*\n\nKoi live match nahi hai abhi.\n\nUpcoming matches dekhne ke liye Schedule pe click karo."
        
        mins = ipl_schedule.minutes_until_match(today_match)
        if mins and mins > 0:
            t1 = today_match.get("t1") or today_match.get("team1") or "?"
            t2 = today_match.get("t2") or today_match.get("team2") or "?"
            return f"🏏 *Today's Match*\n\n*{t1} vs {t2}*\n\n⏰ Starts in {mins} minutes\n\nThrill alerts will start automatically!"
        return "🏏 *Live Score*\n\nMatch data load ho raha hai... Thodi der baad try karo."
    
    t1_prob = _engine_state.get("last_t1_prob") or 50
    t2_prob = _engine_state.get("last_t2_prob") or 50
    thrill = _engine_state.get("last_thrill") or 6.0
    _, reason = calculate_thrill_score(match_data, None)
    
    return alert_manager.live_score_message(match_data, t1_prob, t2_prob, thrill, reason)

def get_schedule_message():
    """Called when user clicks 'Schedule'."""
    all_matches = api_manager.get_today_schedule()
    upcoming = ipl_schedule.get_upcoming_ipl_matches(all_matches, limit=5)
    return alert_manager.upcoming_matches_message(upcoming)

def get_status_message():
    """Admin-only status check."""
    api_status = api_manager.get_status()
    user_count = database.get_user_count()
    
    today_match = _engine_state.get("today_match")
    match_info = "None"
    if today_match:
        t1 = today_match.get("t1") or "?"
        t2 = today_match.get("t2") or "?"
        match_info = f"{t1} vs {t2}"
    
    return (
        f"🤖 *Bot Status*\n\n"
        f"👥 Subscribed Users: {user_count}\n"
        f"📊 API Used: {api_status['calls_used']}/{api_status['limit']}\n"
        f"📅 Today's Match: {match_info}\n"
        f"🎯 Phase: {_engine_state['match_phase']}\n"
        f"🔥 Last Thrill: {_engine_state.get('last_thrill', 'N/A')}/10"
    )
