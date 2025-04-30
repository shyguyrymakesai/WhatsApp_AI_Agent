"""
WhatsApp **and** email reminders:
• 24‑hour and 1‑hour notices
• tracks *reminder_sent_sms* / *reminder_sent_email*
• atomic JSON writes
• runs every 60 s via APScheduler (bootstrapped from `receiver.py`)
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import requests
import dateparser  # lightweight natural‑language dt parser
from apscheduler.schedulers.background import BackgroundScheduler

from src.utils.email import send_email  # thin SMTP helper

# -----------------------------------------------------------------------------
# paths & constants
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[1]
BOOKINGS_FILE = BASE_DIR / "data" / "bookings.json"
WHATSAPP_URL = "http://localhost:3000/send"  # Node sender

# -----------------------------------------------------------------------------
# tiny JSON helpers (load / atomic save)
# -----------------------------------------------------------------------------


def _load() -> dict:
    if not BOOKINGS_FILE.exists():
        return {}
    with BOOKINGS_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def _atomic_save(data: dict) -> None:
    BOOKINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=BOOKINGS_FILE.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    shutil.move(tmp, BOOKINGS_FILE)


# -----------------------------------------------------------------------------
# send helpers
# -----------------------------------------------------------------------------


def _send_sms(number: str, msg: str) -> bool:
    try:
        requests.post(
            WHATSAPP_URL,
            json={"number": number, "message": msg},
            timeout=5,
        )
        print(f"✅ SMS reminder → {number}")
        return True
    except Exception as e:
        print(f"❌ SMS reminder failed → {number}: {e}")
        return False


def _send_email(address: str, slot_str: str, when: str) -> bool:
    subject = "⏰ Appointment reminder"
    body = (
        "Hi there!\n\nThis is a quick reminder that you have an "
        f"appointment {when} at {slot_str}.\n\n"
        "Reply to this email or WhatsApp if you need to reschedule.\n\n"
        "See you soon!"
    )
    try:
        send_email(address, subject, body)
        return True
    except Exception as e:
        print(f"❌ Email reminder failed → {address}: {e}")
        return False


# -----------------------------------------------------------------------------
# utility
# -----------------------------------------------------------------------------


def _parse_slot(slot_str: str) -> datetime | None:
    """Convert stored 'Wednesday 3:15 PM' into the *next* datetime in the future."""
    dt = dateparser.parse(slot_str)
    if not dt:
        return None

    now = datetime.now()
    while dt < now:  # bump to the next occurrence
        dt += timedelta(days=7)
    return dt


# -----------------------------------------------------------------------------
# main job – run every minute
# -----------------------------------------------------------------------------


def check_reminders() -> None:
    now = datetime.now()
    bookings = _load()

    for phone, info in bookings.items():
        slot_str: str | None = info.get("time")
        if not slot_str:
            continue

        slot_dt = _parse_slot(slot_str)
        if not slot_dt:
            continue

        # 24‑hour and 1‑hour windows
        for hrs, sms_flag, email_flag in (
            (24, "reminder_sent_sms_24", "reminder_sent_email_24"),
            (1, "reminder_sent_sms_1", "reminder_sent_email_1"),
        ):
            window_start = slot_dt - timedelta(hours=hrs)
            if window_start <= now < slot_dt:  # we're in the window
                when_txt = "tomorrow" if hrs == 24 else "in 1 hour"
                sms_msg = f"🔔 Friendly reminder: your appointment is {when_txt} at {slot_str}."

                # --- SMS ---
                if not info.get(sms_flag) and _send_sms(phone, sms_msg):
                    info[sms_flag] = True

                # --- Email ---
                email_addr: str | None = info.get("email")
                if email_addr and not info.get(email_flag):
                    if _send_email(email_addr, slot_str, when_txt):
                        info[email_flag] = True

    _atomic_save(bookings)


# -----------------------------------------------------------------------------
# bootstrap called from receiver
# -----------------------------------------------------------------------------


def start_scheduler(app):
    sched = BackgroundScheduler()
    sched.add_job(check_reminders, "interval", minutes=1, id="reminders")
    sched.start()
    app.state._reminder_sched = sched  # survive autoreload during dev
    print("🚀 Reminder scheduler running (checks every 60 s)")
