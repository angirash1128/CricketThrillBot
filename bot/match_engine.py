# match_engine.py
# Ye file IPL matches track karti hai aur exciting moments detect karti hai

import os
import requests

# API credentials environment variables se
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST", "cricbuzz-cricket.p.rapidapi.com")

# API request headers
def get_headers():
    return {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

# ─────────────────────────────────────────
# MATCH DISCOVERY
# ─────────────────────────────────────────

def get_live_ipl_match():
    """
    Cricbuzz API se live IPL 2026 match dhundo
    Sirf 'Indian Premier League 2026' matches return karo
    Returns: match dict ya None
    """
    try:
        url = f"https://{RAPIDAPI_HOST}/matches/v1/live"
        response = requests.get(url, headers=get_headers(), timeout=10)
        
        if response.status_code != 200:
            print(f"❌ API error: {response.status_code}")
            return None
        
        data = response.json()
        
        # Matches list dhundo
        type_matches = data.get("typeMatches", [])
        
        for match_type in type_matches:
            series_matches = match_type.get("seriesMatches", [])
            
            for series in series_matches:
                series_wrapper = series.get("seriesAdWrapper", {})
                series_name = series_wrapper.get("seriesName", "")
                
                # Sirf IPL 2026 matches
                # Flexible IPL detection if "IPL" not in series_name.upper():     continue
                    continue
                
                matches = series_wrapper.get("matches", [])
                
                for match in matches:
                    match_info = match.get("matchInfo", {})
                    match_score = match.get("matchScore", {})
                    
                    # Match ID
                    match_id = str(match_info.get("matchId", ""))
                    
                    # Team names
                    team1 = match_info.get("team1", {}).get("teamName", "Team A")
                    team2 = match_info.get("team2", {}).get("teamName", "Team B")
                    
                    # Match state
                    state = match_info.get("state", "")
                    status = match_info.get("status", "")
                    
                    return {
                        "match_id": match_id,
                        "team1": team1,
                        "team2": team2,
                        "state": state,
                        "status": status,
                        "score_data": match_score
                    }
        
        # Koi IPL match nahi mila
        return None
        
    except Exception as e:
        print(f"❌ get_live_ipl_match error: {e}")
        return None

def get_match_scorecard(match_id):
    """
    Specific match ka detailed scorecard lao
    Wickets, runs, overs sab yahan se milega
    """
    try:
        url = f"https://{RAPIDAPI_HOST}/mcenter/v1/{match_id}/scard"
        response = requests.get(url, headers=get_headers(), timeout=10)
        
        if response.status_code != 200:
            return None
        
        return response.json()
        
    except Exception as e:
        print(f"❌ get_match_scorecard error: {e}")
        return None

# ─────────────────────────────────────────
# SCORE PARSING
# ─────────────────────────────────────────

def parse_current_innings(scorecard_data):
    """
    Scorecard se current innings ki info nikalo
    Returns: dict with wickets, runs, overs, innings_id
    """
    try:
        if not scorecard_data:
            return None
        
        score_card = scorecard_data.get("scoreCard", [])
        
        if not score_card:
            return None
        
        # Last innings = current innings
        current = score_card[-1]
        
        innings_id = current.get("inningsId", 1)
        
        bat_team_details = current.get("batTeamDetails", {})
        bat_score = bat_team_details.get("batTeamScoreDetails", {})
        
        runs = bat_score.get("runs", 0)
        wickets = bat_score.get("wickets", 0)
        overs = bat_score.get("overs", 0.0)
        
        # Target (2nd innings ke liye)
        target = None
        if innings_id == 2:
            match_header = scorecard_data.get("matchHeader", {})
            target = match_header.get("target", None)
        
        return {
            "innings_id": innings_id,
            "runs": runs,
            "wickets": wickets,
            "overs": float(overs),
            "target": target
        }
        
    except Exception as e:
        print(f"❌ parse_current_innings error: {e}")
        return None

# ─────────────────────────────────────────
# THRILL DETECTION
# ─────────────────────────────────────────

# Ye dictionary match ka state track karti hai
# Key: match_id, Value: tracker dict
match_trackers = {}

def get_tracker(match_id):
    """Match ka tracker lao, agar nahi hai to naya banao"""
    if match_id not in match_trackers:
        match_trackers[match_id] = {
            "innings_id": None,        # Current innings
            "wicket_count": 0,         # Wickets track karne ke liye
            "momentum_baseline": 0,    # Momentum ke liye runs baseline
            "thriller_alerted": False, # Thriller alert ek baar hi dena hai
            "super_over_alerted": False,
        }
    return match_trackers[match_id]

def reset_tracker(match_id, new_innings_id):
    """Naya innings aane par tracker reset karo"""
    match_trackers[match_id] = {
        "innings_id": new_innings_id,
        "wicket_count": 0,
        "momentum_baseline": 0,
        "thriller_alerted": False,
        "super_over_alerted": False,
    }
    print(f"🔄 Tracker reset for match {match_id}, innings {new_innings_id}")

def detect_thrills(match_id, innings_data):
    """
    Exciting moments detect karo
    Returns: list of alert dicts
    
    Alert dict format:
    {
        "type": "wicket" / "momentum" / "thriller" / "super_over",
        "is_mega": True/False,
        "message": "Alert message text"
    }
    """
    alerts = []
    
    if not innings_data:
        return alerts
    
    tracker = get_tracker(match_id)
    
    innings_id = innings_data["innings_id"]
    runs = innings_data["runs"]
    wickets = innings_data["wickets"]
    overs = innings_data["overs"]
    target = innings_data["target"]
    
    # ── Innings change check ──
    if tracker["innings_id"] is None:
        # Pehli baar track kar rahe hain
        tracker["innings_id"] = innings_id
        tracker["wicket_count"] = wickets
        tracker["momentum_baseline"] = runs
        return alerts  # Pehle poll mein koi alert nahi
    
    if tracker["innings_id"] != innings_id:
        # Innings badal gayi - tracker reset karo
        reset_tracker(match_id, innings_id)
        tracker = get_tracker(match_id)
        tracker["wicket_count"] = wickets
        tracker["momentum_baseline"] = runs
        return alerts
    
    # ── WICKET ALERT ──
    if wickets > tracker["wicket_count"]:
        new_wickets = wickets - tracker["wicket_count"]
        
        for i in range(new_wickets):
            wicket_num = tracker["wicket_count"] + i + 1
            alerts.append({
                "type": "wicket",
                "is_mega": False,
                "message": (
                    f"🚨 WICKET ALERT!\n\n"
                    f"Wicket #{wicket_num} down!\n"
                    f"Score: {runs}/{wickets}\n"
                    f"Overs: {overs}"
                )
            })
        
        tracker["wicket_count"] = wickets
    
    # ── MOMENTUM SHIFT ──
    runs_since_baseline = runs - tracker["momentum_baseline"]
    
    if runs_since_baseline >= 12:
        alerts.append({
            "type": "momentum",
            "is_mega": False,
            "message": (
                f"⚡ MOMENTUM SHIFT!\n\n"
                f"{runs_since_baseline} runs scored rapidly!\n"
                f"Score: {runs}/{wickets}\n"
                f"Overs: {overs}"
            )
        })
        # Baseline reset karo
        tracker["momentum_baseline"] = runs
    
    # ── THRILLER FINISH ──
    if (
        not tracker["thriller_alerted"]
        and innings_id == 2
        and target
        and overs >= 17.0  # Last 3 overs
    ):
        runs_needed = target - runs
        balls_left = max(1, int((20 - overs) * 6))
        rrr = (runs_needed * 6) / balls_left  # Required run rate
        
        if rrr > 10 and runs_needed > 0:
            alerts.append({
                "type": "thriller",
                "is_mega": False,
                "message": (
                    f"🔴 THRILLER FINISH!\n\n"
                    f"Last 3 overs!\n"
                    f"Need {runs_needed} runs from {balls_left} balls\n"
                    f"Required Rate: {rrr:.1f} per over\n"
                    f"Can they do it? 🏏"
                )
            })
            tracker["thriller_alerted"] = True
    
    return alerts
