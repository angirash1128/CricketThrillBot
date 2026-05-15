import os
import requests
import time
import threading
from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")
CRICAPI_KEY = os.environ.get("CRICAPI_KEY", "")
BASE_URL = "https://api.cricapi.com/v1"

_lock = threading.Lock()

_state = {
    "api_count": 0,
    "last_reset_date": datetime.now(IST).strftime("%Y-%m-%d"),
    "cache": {},
    "last_call_time": 0
}

DAILY_LIMIT = 95
MIN_GAP_SECONDS = 2
CACHE_DURATION = 60

def _reset_if_new_day():
    today = datetime.now(IST).strftime("%Y-%m-%d")
    if _state["last_reset_date"] != today:
        _state["api_count"] = 0
        _state["last_reset_date"] = today
        _state["cache"] = {}
        print(f"[API] Daily counter reset for {today}")

def get_api_count():
    with _lock:
        _reset_if_new_day()
        return _state["api_count"]

def can_call():
    with _lock:
        _reset_if_new_day()
        return _state["api_count"] < DAILY_LIMIT

def _make_cache_key(endpoint, params):
    param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if k != "apikey")
    return f"{endpoint}?{param_str}"

def fetch(endpoint, params=None, force_fresh=False, cache_seconds=None):
    if params is None:
        params = {}
    
    with _lock:
        _reset_if_new_day()
        
        cache_key = _make_cache_key(endpoint, params)
        
        if not force_fresh and cache_key in _state["cache"]:
            cached = _state["cache"][cache_key]
            age = time.time() - cached["time"]
            duration = cache_seconds if cache_seconds is not None else CACHE_DURATION
            if age < duration:
                print(f"[API] Cache hit: {endpoint} (age: {int(age)}s)")
                return cached["data"]
        
        if _state["api_count"] >= DAILY_LIMIT:
            print(f"[API] Daily limit reached ({DAILY_LIMIT}). Skipping call.")
            if cache_key in _state["cache"]:
                return _state["cache"][cache_key]["data"]
            return None
        
        gap = time.time() - _state["last_call_time"]
        if gap < MIN_GAP_SECONDS:
            time.sleep(MIN_GAP_SECONDS - gap)
        
        params["apikey"] = CRICAPI_KEY
        
        try:
            r = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
            _state["api_count"] += 1
            _state["last_call_time"] = time.time()
            
            print(f"[API] Call #{_state['api_count']}: {endpoint}")
            
            response = r.json()
            
            if response.get("status") == "success":
                data = response.get("data", [])
                _state["cache"][cache_key] = {
                    "data": data,
                    "time": time.time()
                }
                return data
            else:
                print(f"[API] Failed response: {response.get('reason', 'unknown')}")
                return None
                
        except Exception as e:
            print(f"[API] Error: {e}")
            return None

def get_today_schedule():
    return fetch("cricScore", cache_seconds=3600)

def get_match_info(match_id):
    return fetch("match_info", params={"id": match_id}, cache_seconds=30)

def get_match_squad(match_id):
    return fetch("match_squad", params={"id": match_id}, cache_seconds=86400)

def get_status():
    return {
        "calls_used": get_api_count(),
        "calls_remaining": DAILY_LIMIT - get_api_count(),
        "limit": DAILY_LIMIT,
        "reset_date": _state["last_reset_date"]
    }
