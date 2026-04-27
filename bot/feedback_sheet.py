# feedback_sheet.py
# Ye file Google Sheets mein user feedback save karti hai

import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Google Sheets ka naam
SHEET_NAME = "Cricket Thrill Alert - Feedback"

# Google API ke liye permissions (scopes)
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

def get_sheet():
    """
    Google Sheets se connect karo aur sheet return karo
    GOOGLE_SERVICE_ACCOUNT env variable se credentials lao
    """
    try:
        # Environment variable se JSON credentials lao
        service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT")
        
        if not service_account_json:
            print("❌ GOOGLE_SERVICE_ACCOUNT env variable nahi mili")
            return None
        
        # JSON string ko dict mein convert karo
        service_account_info = json.loads(service_account_json)
        
        # Credentials banao
        creds = Credentials.from_service_account_info(
            service_account_info, 
            scopes=SCOPES
        )
        
        # Google Sheets se connect karo
        client = gspread.authorize(creds)
        
        # Sheet kholo
        sheet = client.open(SHEET_NAME).sheet1
        
        return sheet
        
    except Exception as e:
        print(f"❌ Google Sheets connection error: {e}")
        return None

def setup_sheet_headers():
    """
    Sheet mein headers add karo agar pehle se nahi hain
    Columns: User ID | Name | Rating | Feedback | Date
    """
    try:
        sheet = get_sheet()
        if not sheet:
            return
        
        # Pehli row check karo
        first_row = sheet.row_values(1)
        
        # Agar headers nahi hain to add karo
        if not first_row or first_row[0] != "User ID":
            sheet.insert_row(
                ["User ID", "Name", "Rating", "Feedback", "Date"], 
                1
            )
            print("✅ Google Sheet headers set")
            
    except Exception as e:
        print(f"❌ Sheet header setup error: {e}")

def save_feedback(user_id, name, rating, feedback_text):
    """
    User ka feedback Google Sheets mein save karo
    
    Parameters:
    - user_id: Telegram user ID
    - name: User ka naam
    - rating: 1 se 5 stars
    - feedback_text: User ne jo likha
    """
    try:
        sheet = get_sheet()
        if not sheet:
            print("❌ Sheet nahi mili, feedback save nahi hua")
            return False
        
        # Date aur time
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Row add karo sheet mein
        sheet.append_row([
            str(user_id),
            name,
            f"{rating} ⭐",
            feedback_text,
            now
        ])
        
        print(f"✅ Feedback saved for user {user_id}")
        return True
        
    except Exception as e:
        print(f"❌ Feedback save error: {e}")
        return False