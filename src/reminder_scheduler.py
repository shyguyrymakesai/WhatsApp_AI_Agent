import json
import os
import time
from datetime import datetime
import requests

BOOKINGS_FILE = "data/bookings.json"
WHATSAPP_SERVER_URL = "http://localhost:3000/send"


def load_bookings():
    if not os.path.exists(BOOKINGS_FILE):
        return {}
    with open(BOOKINGS_FILE, "r") as f:
        return json.load(f)


def save_bookings(bookings):
    with open(BOOKINGS_FILE, "w") as f:
        json.dump(bookings, f, indent=4)


def send_whatsapp_reminder(number, time_str):
    message = f"🔔 Friendly reminder: You have an appointment scheduled for {time_str}! Reply if you need to reschedule."
    payload = {"number": number, "message": message}
    try:
        res = requests.post(WHATSAPP_SERVER_URL, json=payload)
        res.raise_for_status()
        print(f"✅ Reminder sent to {number} for {time_str}")
    except Exception as e:
        print(f"❌ Failed to send reminder to {number}: {e}")


def check_and_send_reminders():
    bookings = load_bookings()
    now = datetime.now()

    for customer_id, data in bookings.items():
        if not data.get("reminder_sent"):
            try:
                reminder_time = datetime.strptime(data["reminder_time"], "%A %I:%M %p")
            except Exception as e:
                print(f"⚠️ Could not parse reminder time for {customer_id}: {e}")
                continue

            if now >= reminder_time:
                send_whatsapp_reminder(data["customer_id"], data["time"])
                data["reminder_sent"] = True

    save_bookings(bookings)


# 🔥 MAIN RUNNER 🔥
def run_scheduler():
    print("🚀 Reminder scheduler running... Checking every 60 seconds!")
    while True:
        check_and_send_reminders()
        time.sleep(60)
