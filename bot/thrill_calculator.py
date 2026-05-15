def safe_float(val, default=0.0):
    try:
        return float(val)
    except:
        return default

def safe_int(val, default=0):
    try:
        return int(val)
    except:
        return default

def calculate_win_probability(match_data):
    """
    Returns: (team1_prob, team2_prob, source)
    source = "api" if API gave it, else "calculated"
    """
    api_prob = match_data.get("win_probability") or match_data.get("winProbability")
    if api_prob:
        try:
            t1 = float(api_prob.get("team1", 50))
            t2 = float(api_prob.get("team2", 50))
            return round(t1, 1), round(t2, 1), "api"
        except:
            pass
    
    score_data = match_data.get("score", [])
    if not score_data:
        return 50.0, 50.0, "calculated"
    
    if len(score_data) < 2:
        return 50.0, 50.0, "calculated"
    
    inn1 = score_data[0]
    inn2 = score_data[1]
    
    target = safe_int(inn1.get("r", 0)) + 1
    chase_runs = safe_int(inn2.get("r", 0))
    chase_wickets = safe_int(inn2.get("w", 0))
    chase_overs = safe_float(inn2.get("o", 0))
    
    runs_needed = target - chase_runs
    wickets_left = 10 - chase_wickets
    
    total_overs = 20
    overs_done = chase_overs
    balls_done = int(overs_done) * 6 + int(round((overs_done - int(overs_done)) * 10))
    balls_left = (total_overs * 6) - balls_done
    
    if runs_needed <= 0:
        return 0.0, 100.0, "calculated"
    if wickets_left <= 0 or balls_left <= 0:
        return 100.0, 0.0, "calculated"
    
    rrr = (runs_needed * 6) / balls_left if balls_left > 0 else 99
    
    chase_score = 50.0
    
    if rrr < 6:
        chase_score += 25
    elif rrr < 8:
        chase_score += 15
    elif rrr < 10:
        chase_score += 5
    elif rrr < 12:
        chase_score -= 10
    elif rrr < 15:
        chase_score -= 25
    else:
        chase_score -= 40
    
    if wickets_left >= 8:
        chase_score += 10
    elif wickets_left >= 6:
        chase_score += 5
    elif wickets_left >= 4:
        chase_score -= 5
    elif wickets_left >= 2:
        chase_score -= 15
    else:
        chase_score -= 25
    
    pressure_factor = (balls_left / 120) * 10
    if rrr > 10:
        chase_score -= (10 - pressure_factor)
    
    chase_score = max(2, min(98, chase_score))
    bowl_score = 100 - chase_score
    
    chasing_team_name = inn2.get("inning", "")
    team1_name = match_data.get("t1") or match_data.get("team1") or ""
    
    if team1_name and team1_name.lower() in chasing_team_name.lower():
        return round(chase_score, 1), round(bowl_score, 1), "calculated"
    else:
        return round(bowl_score, 1), round(chase_score, 1), "calculated"

def calculate_thrill_score(match_data, prev_probability=None):
    """
    Returns: (thrill_score_out_of_10, reason_text)
    """
    score_data = match_data.get("score", [])
    
    if not score_data:
        return 7.0, "Match yet to start, potential excitement ahead."
    
    t1_prob, t2_prob, _ = calculate_win_probability(match_data)
    
    closeness = 100 - abs(t1_prob - t2_prob)
    closeness_score = (closeness / 100) * 4.0
    
    pressure_score = 0.0
    momentum_score = 0.0
    phase_score = 1.0
    
    if len(score_data) >= 2:
        inn1 = score_data[0]
        inn2 = score_data[1]
        
        target = safe_int(inn1.get("r", 0)) + 1
        chase_runs = safe_int(inn2.get("r", 0))
        chase_wickets = safe_int(inn2.get("w", 0))
        chase_overs = safe_float(inn2.get("o", 0))
        
        runs_needed = target - chase_runs
        balls_done = int(chase_overs) * 6 + int(round((chase_overs - int(chase_overs)) * 10))
        balls_left = 120 - balls_done
        
        if balls_left > 0 and runs_needed > 0:
            rrr = (runs_needed * 6) / balls_left
            crr = (chase_runs * 6) / balls_done if balls_done > 0 else 0
            
            pressure_diff = abs(rrr - crr)
            if pressure_diff < 1:
                pressure_score = 3.0
            elif pressure_diff < 2.5:
                pressure_score = 2.5
            elif pressure_diff < 4:
                pressure_score = 2.0
            elif pressure_diff < 6:
                pressure_score = 1.5
            else:
                pressure_score = 1.0
        
        if chase_overs >= 16:
            phase_score = 2.0
        elif chase_overs >= 12:
            phase_score = 1.5
        elif chase_overs >= 6:
            phase_score = 1.0
        else:
            phase_score = 0.5
    
    elif len(score_data) == 1:
        inn = score_data[0]
        runs = safe_int(inn.get("r", 0))
        wickets = safe_int(inn.get("w", 0))
        overs = safe_float(inn.get("o", 0))
        
        if overs > 0:
            crr = runs / overs
            if crr > 10:
                pressure_score = 2.5
            elif crr > 8:
                pressure_score = 2.0
            else:
                pressure_score = 1.5
        
        if overs >= 16:
            phase_score = 1.5
        elif overs >= 10:
            phase_score = 1.0
        else:
            phase_score = 0.7
    
    if prev_probability:
        prev_t1, prev_t2 = prev_probability[0], prev_probability[1]
        swing = abs(t1_prob - prev_t1)
        if swing >= 20:
            momentum_score = 2.0
        elif swing >= 10:
            momentum_score = 1.5
        elif swing >= 5:
            momentum_score = 1.0
        else:
            momentum_score = 0.3
    
    total = closeness_score + pressure_score + momentum_score + phase_score
    total = max(1.0, min(10.0, total))
    
    reason = generate_thrill_reason(closeness, pressure_score, momentum_score, phase_score)
    
    return round(total, 1), reason

def generate_thrill_reason(closeness, pressure, momentum, phase):
    reasons = []
    
    if closeness >= 80:
        reasons.append("Match is in a near 50-50 zone")
    elif closeness >= 60:
        reasons.append("Both teams in contention")
    elif closeness >= 40:
        reasons.append("One team slightly ahead")
    else:
        reasons.append("Match looks one-sided")
    
    if pressure >= 2.5:
        reasons.append("high chase pressure")
    elif pressure >= 1.5:
        reasons.append("building pressure")
    
    if momentum >= 1.5:
        reasons.append("momentum just shifted")
    
    if phase >= 2.0:
        reasons.append("entering death overs")
    
    return ", ".join(reasons).capitalize() + "."

def detect_probability_swing(current_t1_prob, prev_t1_prob):
    if prev_t1_prob is None:
        return 0
    return abs(current_t1_prob - prev_t1_prob)

def get_polling_interval(thrill_score, match_phase, prob_swing):
    """
    Returns polling interval in seconds based on match state.
    match_phase: "early", "mid", "death", "innings_break", "pre_match"
    """
    if match_phase == "innings_break":
        return 600
    
    if match_phase == "pre_match":
        return 300
    
    if prob_swing >= 20:
        return 120
    
    if thrill_score >= 9.0:
        return 120
    elif thrill_score >= 8.0:
        return 180
    elif thrill_score >= 7.0:
        return 300
    
    if match_phase == "death":
        return 180
    elif match_phase == "mid":
        return 420
    elif match_phase == "early":
        return 600
    
    return 600

def get_match_phase(score_data):
    if not score_data:
        return "pre_match"
    
    latest_inn = score_data[-1]
    overs = safe_float(latest_inn.get("o", 0))
    
    if overs >= 16:
        return "death"
    elif overs >= 10:
        return "mid"
    elif overs > 0:
        return "early"
    else:
        return "pre_match"
