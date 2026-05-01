import os
import time
import threading
from datetime import datetime
from telebot import TeleBot, types
from match_engine import get_live_ipl_match, get_match_scorecard, parse_current_innings

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = TeleBot(TOKEN)

def match_poll_loop():
    print("🚀 Thrill Hunter Engine Started")
    current_mid = None
    
    while True:
        try:
            now = datetime.now()
            # 1. API Safety: Raat 12 se Sham 7 tak API ko hath bhi nahi lagana
            if now.hour < 19:
                time.sleep(3600) # Check every hour (0 API calls)
                continue

            # 2. Get Match
            match = get_live_ipl_match()
            if not match:
                time.sleep(1800) # Match nahi hai toh 30 min wait
                continue

            mid = match["match_id"]
            scard = get_match_scorecard(mid)
            data = parse_current_innings(scard)

            if data:
                # 3. Smart Polling Logic
                # Agar match climax par hai (16th over ke baad), toh poll faster
                if data["overs"] > 16.0 or (data["innings_id"] == 2 and data["overs"] > 12.0):
                    wait_time = 300 # Har 5 minute
                else:
                    wait_time = 900 # Normal time mein har 15 minute

                # 4. Thrill Alert! (Example: Collapse or High Run Rate)
                if data["wickets"] >= 8:
                    bot.send_message(YOUR_ADMIN_ID_OR_CHANNEL, "🚨 THRILL ALERT: Batting Collapse! Check Match! 🏏")

                print(f"Match: {match['team1']} - Polling in {wait_time/60} mins")
                time.sleep(wait_time)

        except Exception as e:
            time.sleep(600)

if __name__ == "__main__":
    threading.Thread(target=match_poll_loop, daemon=True).start()
    bot.infinity_polling()
