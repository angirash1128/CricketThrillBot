import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")
SHEET_ID = "13yTetfXOcupUVI2Dr-4EOnGzZ0OeOhuNbLKTgcRYWEk"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_sheet = None

def get_sheet():
    global _sheet
    if _sheet is not None:
        return _sheet
    try:
        creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT", "")
        if not creds_json:
            return None
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        _sheet = client.open_by_key(SHEET_ID).sheet1
        return _sheet
    except Exception as e:
        print(f"[Sheet Error] {e}")
        return None

def log_feedback(user_id, username, match_name, thrill_score, rating, comment=""):
    try:
        sheet = get_sheet()
        if not sheet:
            return False
        now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([now, str(user_id), username, match_name, thrill_score, rating, comment])
        return True
    except Exception as e:
        print(f"[Feedback Error] {e}")
        return False

def log_match_summary(match_id, team1, team2, winner, thrill_score, api_calls_used):
    try:
        sheet = get_sheet()
        if not sheet:
            return False
        now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([now, "MATCH_LOG", str(match_id), f"{team1} vs {team2}", winner, thrill_score, f"API: {api_calls_used}"])
        return True
    except Exception as e:
        print(f"[Match Log Error] {e}")
        return False
