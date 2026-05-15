import pytz
from datetime import datetime
from thrill_calculator import safe_float, safe_int

IST = pytz.timezone("Asia/Kolkata")

def _get_team_names(match_data):
    t1 = match_data.get("t1") or match_data.get("team1") or "Team A"
    t2 = match_data.get("t2") or match_data.get("team2") or "Team B"
    return t1, t2

def _format_overs(overs_float):
    try:
        whole = int(overs_float)
        balls = int(round((overs_float - whole) * 10))
        return f"{whole}.{balls}"
    except:
        return str(overs_float)

def _watch_verdict(thrill):
    if thrill >= 9.0:
        return "🔥 Don't miss this — pure drama!"
    elif thrill >= 8.0:
        return "👀 Highly recommended to watch."
    elif thrill >= 7.0:
        return "✅ Worth watching."
    elif thrill >= 5.5:
        return "👍 Decent contest."
    else:
        return "😐 Casual watch only."

def upcoming_matches_message(matches):
    if not matches:
        return "📅 *Upcoming Matches*\n\nKoi upcoming match nahi mila. Refresh ho raha hai... ⏳"
    
    lines = ["🏏 *Upcoming Matches*", "─" * 20, ""]
    
    for i, m in enumerate(matches[:5], 1):
        t1, t2 = _get_team_names(m)
        date_str = m.get("date_ist", "TBD")
        time_str = m.get("time_ist", "TBD")
        venue = m.get("venue", "TBD")
        series = m.get("series", "")
        
        lines.append(f"*{i}) {t1} vs {t2}*")
        lines.append(f"📅 {date_str}")
        lines.append(f"⏰ {time_str} IST")
        if venue and venue != "TBD":
            lines.append(f"🏟 {venue}")
        if series:
            lines.append(f"🏆 {series}")
        lines.append("")
    
    return "\n".join(lines)

def toss_alert_message(match_data, t1_prob, t2_prob, thrill, reason):
    t1, t2 = _get_team_names(match_data)
    venue = match_data.get("venue", "")
    series = match_data.get("series", "")
    toss_info = match_data.get("tossWinner", "")
    toss_choice = match_data.get("tossChoice", "")
    match_time = match_data.get("dateTimeGMT", "")
    
    try:
        if match_time:
            dt = datetime.strptime(match_time, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=pytz.utc).astimezone(IST)
            time_str = dt.strftime("%I:%M %p")
        else:
            time_str = "TBD"
    except:
        time_str = "TBD"
    
    msg = [
        "🚨 *Today's Match Alert*",
        "",
        f"🏏 *{t1} vs {t2}*",
    ]
    if series:
        msg.append(f"🏆 {series}")
    if venue:
        msg.append(f"📍 {venue}")
    msg.append(f"⏰ Match Start: {time_str} IST")
    msg.append("")
    
    if toss_info and toss_choice:
        msg.append(f"🪙 *Toss Update:*")
        msg.append(f"{toss_info} won the toss and chose to {toss_choice}.")
    else:
        msg.append("🪙 Toss update awaited...")
    
    msg.append("")
    msg.append(f"📊 *Win Probability:*")
    msg.append(f"{t1}: {t1_prob}%")
    msg.append(f"{t2}: {t2_prob}%")
    msg.append("")
    msg.append(f"🔥 *Thrill Alert: {thrill}/10*")
    msg.append(f"_Reason: {reason}_")
    msg.append("")
    msg.append(f"👀 *Worth Watching?*")
    msg.append(_watch_verdict(thrill))
    
    return "\n".join(msg)

def match_start_message(match_data, t1_prob, t2_prob, thrill):
    t1, t2 = _get_team_names(match_data)
    score_data = match_data.get("score", [])
    
    msg = [
        "▶️ *Match Started*",
        "",
        f"🏏 *{t1} vs {t2}*",
    ]
    
    if score_data:
        inn = score_data[0]
        batting = inn.get("inning", "").split(" Inning")[0]
        msg.append(f"{batting} batting first")
        msg.append("")
        msg.append(f"Score: {safe_int(inn.get('r', 0))}/{safe_int(inn.get('w', 0))} ({_format_overs(safe_float(inn.get('o', 0)))})")
    
    msg.append("")
    msg.append(f"📊 *Win Probability:*")
    msg.append(f"{t1}: {t1_prob}%")
    msg.append(f"{t2}: {t2_prob}%")
    msg.append("")
    msg.append(f"🔥 *Thrill Alert: {thrill}/10*")
    msg.append("Status: Match is live now.")
    
    return "\n".join(msg)

def live_score_message(match_data, t1_prob, t2_prob, thrill, reason):
    t1, t2 = _get_team_names(match_data)
    score_data = match_data.get("score", [])
    status = match_data.get("status", "Live")
    
    msg = [
        "📡 *Live Score*",
        "",
        f"🏏 *{t1} vs {t2}*",
        ""
    ]
    
    if not score_data:
        msg.append("Score loading...")
        msg.append("")
        msg.append(f"Status: {status}")
        return "\n".join(msg)
    
    if len(score_data) == 1:
        inn = score_data[0]
        batting_team = inn.get("inning", "").replace(" Inning 1", "").replace(" Inning", "")
        bowling_team = t2 if batting_team.strip() in t1 else t1
        
        runs = safe_int(inn.get("r", 0))
        wickets = safe_int(inn.get("w", 0))
        overs = safe_float(inn.get("o", 0))
        crr = (runs / overs) if overs > 0 else 0
        
        msg.append(f"{batting_team} batting | {bowling_team} bowling")
        msg.append("")
        msg.append(f"Score: {runs}/{wickets} ({_format_overs(overs)})")
        msg.append(f"CRR: {crr:.2f}")
        
        if overs > 0:
            projected = (runs / overs) * 20
            msg.append(f"Projected: {int(projected - 10)}–{int(projected + 10)}")
    
    elif len(score_data) >= 2:
        inn1 = score_data[0]
        inn2 = score_data[1]
        
        target = safe_int(inn1.get("r", 0)) + 1
        chase_runs = safe_int(inn2.get("r", 0))
        chase_wickets = safe_int(inn2.get("w", 0))
        chase_overs = safe_float(inn2.get("o", 0))
        
        chasing_team = inn2.get("inning", "").replace(" Inning 2", "").replace(" Inning", "")
        bowling_team = t2 if chasing_team.strip() in t1 else t1
        
        balls_done = int(chase_overs) * 6 + int(round((chase_overs - int(chase_overs)) * 10))
        balls_left = 120 - balls_done
        runs_needed = target - chase_runs
        
        crr = (chase_runs * 6 / balls_done) if balls_done > 0 else 0
        rrr = (runs_needed * 6 / balls_left) if balls_left > 0 else 0
        
        msg.append(f"{chasing_team} batting | {bowling_team} bowling")
        msg.append("")
        msg.append(f"Target: {target}")
        msg.append(f"Score: {chase_runs}/{chase_wickets} ({_format_overs(chase_overs)})")
        msg.append("")
        msg.append(f"CRR: {crr:.2f}")
        msg.append(f"RRR: {rrr:.2f}")
        msg.append(f"Need: {runs_needed} runs in {balls_left} balls")
    
    msg.append("")
    msg.append(f"📊 *Win Probability:*")
    msg.append(f"{t1}: {t1_prob}%")
    msg.append(f"{t2}: {t2_prob}%")
    msg.append("")
    msg.append(f"🔥 *Thrill Alert: {thrill}/10*")
    msg.append(f"_Reason: {reason}_")
    
    return "\n".join(msg)

def turning_point_alert(match_data, t1_prob, t2_prob, thrill, reason, swing_amount):
    t1, t2 = _get_team_names(match_data)
    score_data = match_data.get("score", [])
    
    msg = [
        "🚨 *Turning Point!*",
        "",
        f"🏏 *{t1} vs {t2}*",
        "",
        f"Big shift in the match! Probability swung by {swing_amount:.0f}%."
    ]
    
    if score_data:
        latest = score_data[-1]
        runs = safe_int(latest.get("r", 0))
        wickets = safe_int(latest.get("w", 0))
        overs = safe_float(latest.get("o", 0))
        msg.append("")
        msg.append(f"Score: {runs}/{wickets} ({_format_overs(overs)})")
    
    msg.append("")
    msg.append(f"📊 *Updated Probability:*")
    msg.append(f"{t1}: {t1_prob}%")
    msg.append(f"{t2}: {t2_prob}%")
    msg.append("")
    msg.append(f"🔥 *Thrill Alert: {thrill}/10*")
    msg.append(f"_{reason}_")
    
    return "\n".join(msg)

def thrill_rising_alert(match_data, t1_prob, t2_prob, thrill, reason):
    t1, t2 = _get_team_names(match_data)
    score_data = match_data.get("score", [])
    
    msg = [
        "⚡ *Thrill Rising!*",
        "",
        f"🏏 *{t1} vs {t2}*",
        ""
    ]
    
    if len(score_data) >= 2:
        inn1 = score_data[0]
        inn2 = score_data[1]
        target = safe_int(inn1.get("r", 0)) + 1
        chase_runs = safe_int(inn2.get("r", 0))
        chase_overs = safe_float(inn2.get("o", 0))
        balls_done = int(chase_overs) * 6 + int(round((chase_overs - int(chase_overs)) * 10))
        balls_left = 120 - balls_done
        runs_needed = target - chase_runs
        rrr = (runs_needed * 6 / balls_left) if balls_left > 0 else 0
        
        msg.append(f"Need {runs_needed} runs in {balls_left} balls")
        msg.append(f"RRR: {rrr:.2f}")
        msg.append("")
    
    msg.append(f"📊 {t1}: {t1_prob}% | {t2}: {t2_prob}%")
    msg.append(f"🔥 *Thrill: {thrill}/10*")
    msg.append(f"_{reason}_")
    msg.append("")
    msg.append("👀 Tune in now — match heating up!")
    
    return "\n".join(msg)

def innings_break_message(match_data, t1_prob, t2_prob, thrill):
    t1, t2 = _get_team_names(match_data)
    score_data = match_data.get("score", [])
    
    msg = [
        "⏸ *Innings Break*",
        "",
        f"🏏 *{t1} vs {t2}*",
        ""
    ]
    
    if score_data:
        inn1 = score_data[0]
        runs = safe_int(inn1.get("r", 0))
        wickets = safe_int(inn1.get("w", 0))
        overs = safe_float(inn1.get("o", 0))
        target = runs + 1
        rrr = (target * 6 / 120)
        
        batting_team = inn1.get("inning", "").replace(" Inning 1", "").replace(" Inning", "")
        chasing_team = t2 if batting_team.strip() in t1 else t1
        
        msg.append(f"{batting_team} finished at {runs}/{wickets} ({_format_overs(overs)})")
        msg.append("")
        msg.append(f"{chasing_team} need {target} runs to win.")
        msg.append(f"Required Run Rate: {rrr:.2f}")
    
    msg.append("")
    msg.append(f"📊 *Win Probability:*")
    msg.append(f"{t1}: {t1_prob}%")
    msg.append(f"{t2}: {t2_prob}%")
    msg.append("")
    msg.append(f"🔥 *Thrill Alert: {thrill}/10*")
    
    return "\n".join(msg)

def super_over_alert(match_data):
    t1, t2 = _get_team_names(match_data)
    return (
        "🚨 *SUPER OVER ALERT!*\n\n"
        f"🏏 *{t1} vs {t2}*\n\n"
        "The match is tied! Super Over coming up.\n\n"
        f"📊 {t1}: 50% | {t2}: 50%\n\n"
        "🔥 *Thrill Alert: 10/10*\n"
        "_Ultimate cricket drama!_\n\n"
        "👀 Switch on the TV right now!"
    )

def rain_delay_message(match_data, t1_prob, t2_prob, thrill):
    t1, t2 = _get_team_names(match_data)
    score_data = match_data.get("score", [])
    
    msg = [
        "🌧 *Match Update*",
        "",
        f"🏏 *{t1} vs {t2}*",
        "",
        "Play has been stopped due to rain.",
        ""
    ]
    
    if score_data:
        latest = score_data[-1]
        runs = safe_int(latest.get("r", 0))
        wickets = safe_int(latest.get("w", 0))
        overs = safe_float(latest.get("o", 0))
        msg.append(f"Current: {runs}/{wickets} ({_format_overs(overs)})")
    
    msg.append("")
    msg.append(f"📊 {t1}: {t1_prob}% | {t2}: {t2_prob}%")
    msg.append(f"🔥 *Thrill: {thrill}/10*")
    msg.append("Status: Match paused.")
    
    return "\n".join(msg)

def match_result_message(match_data, final_thrill, winner_reason="Strong all-round performance"):
    t1, t2 = _get_team_names(match_data)
    score_data = match_data.get("score", [])
    status = match_data.get("status", "")
    
    msg = [
        "✅ *Match Result*",
        "",
        f"🏏 *{t1} vs {t2}*",
        ""
    ]
    
    for inn in score_data:
        team = inn.get("inning", "").replace(" Inning 1", "").replace(" Inning 2", "").replace(" Inning", "")
        runs = safe_int(inn.get("r", 0))
        wickets = safe_int(inn.get("w", 0))
        overs = _format_overs(safe_float(inn.get("o", 0)))
        msg.append(f"{team}: {runs}/{wickets} ({overs})")
    
    msg.append("")
    msg.append(f"🏆 {status}")
    msg.append("")
    msg.append(f"📌 *Main Reason:*")
    msg.append(winner_reason)
    msg.append("")
    msg.append("📊 *Match Analysis:*")
    
    if final_thrill >= 8.5:
        msg.append("- Match Type: Close Fight")
        msg.append("- Momentum Swings: Multiple")
        msg.append("- Finish: Nail-biting")
    elif final_thrill >= 7:
        msg.append("- Match Type: Competitive")
        msg.append("- Momentum Swings: Some")
        msg.append("- Finish: Decent")
    else:
        msg.append("- Match Type: One-sided")
        msg.append("- Momentum Swings: Few")
        msg.append("- Finish: Predictable")
    
    msg.append("")
    msg.append(f"🔥 *Final Thrill Rating: {final_thrill}/10*")
    msg.append("")
    msg.append(f"👀 *Verdict:* {_watch_verdict(final_thrill)}")
    
    return "\n".join(msg)

def daily_summary_message(matches_today):
    if not matches_today:
        return "📋 *Today's Summary*\n\nKoi match khatam nahi hua aaj."
    
    msg = ["📋 *Today's Match Summary*", ""]
    
    most_thrilling = None
    max_thrill = 0
    
    for i, m in enumerate(matches_today, 1):
        t1, t2, winner, thrill, summary = m
        msg.append(f"*{i}) {t1} vs {t2}*")
        msg.append(f"Winner: {winner}")
        msg.append(f"Thrill Rating: {thrill}/10")
        msg.append(f"Result: {summary}")
        msg.append("")
        
        if thrill > max_thrill:
            max_thrill = thrill
            most_thrilling = f"{t1} vs {t2}"
    
    if most_thrilling:
        msg.append("─" * 20)
        msg.append(f"🔥 *Most Thrilling Match:*")
        msg.append(f"{most_thrilling} ({max_thrill}/10)")
    
    return "\n".join(msg)

def admin_alert(message_text, api_count=None):
    msg = ["🔔 *Admin Notification*", "", message_text]
    if api_count is not None:
        msg.append("")
        msg.append(f"API Calls Used: {api_count}/95")
    return "\n".join(msg)

def feedback_request(match_name):
    return (
        f"📝 *Feedback*\n\n"
        f"Match khatam: *{match_name}*\n\n"
        "Aapko hamara Thrill Alert kaisa laga?\n"
        "Niche button dabake batao 👇"
    )
