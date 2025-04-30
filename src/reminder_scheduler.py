"""reminder_scheduler.py
WhatsApp **and** email reminders:
• 24‑hour and 1‑hour notices
• tracks *reminder_sent_sms* / *reminder_sent_email*
• atomic JSON writes
• runs every 60 s via APScheduler (already bootstrapped in receiver)
"""

from __future__ import annotations

import json, os, shutil, tempfile, requests
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
import dateparser  # lightweight natural‑language dt parser

from utils.email import send_email  # ← NEW helper

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
# send functions
# -----------------------------------------------------------------------------


def _send_sms(number: str, msg: str) -> bool:
    try:
        requests.post(WHATSAPP_URL, json={"number": number, "message": msg}, timeout=5)
        print(f"✅ SMS reminder → {number}")
        return True
    except Exception as e:
        print(f"❌ SMS reminder failed → {number}: {e}")
        return False


def _send_email(address: str, slot_str: str) -> bool:
    subj = "⏰ Appointment reminder"
    body = (
        "Hi there!\n\nJust a heads‑up that you have an appointment scheduled "
        f"for {slot_str}.\n\nReply to this email or WhatsApp if you need to "
        "reschedule.\n\nSee you soon!"
    )
    try:
        send_email(address, subj, body)
        return True
    except Exception as e:
        print(f"❌ Email reminder failed → {address}: {e}")
        return False


# -----------------------------------------------------------------------------
# main job – run every minute
# -----------------------------------------------------------------------------


def _parse_slot(slot_str: str) -> datetime | None:
    """Convert stored 'Wednesday 3:15 PM' into next datetime in the future."""
    dt = dateparser.parse(slot_str)
    if not dt:
        return None
    now = datetime.now()
    # if parsed time already happened today, bump to next week
    while dt < now:
        dt += timedelta(days=7)
    return dt


def check_reminders() -> None:
    now = datetime.now()
    bookings = _load()

    for phone, data in bookings.items():
        slot_str: str | None = data.get("time")
        if not slot_str:
            continue

        slot_dt = _parse_slot(slot_str)
        if not slot_dt:
            continue

        # 24 h & 1 h windows
        for hrs, sms_flag, email_flag in (
            (24, "reminder_sent_sms_24", "reminder_sent_email_24"),
            (1, "reminder_sent_sms_1", "reminder_sent_email_1"),
        ):
            if slot_dt - timedelta(hours=hrs) <= now < slot_dt:
                # --- SMS ---
                if not data.get(sms_flag):
                    txt = (
                        "🔔 Friendly reminder: your appointment is "
                        + ("tomorrow" if hrs == 24 else "in 1 hour")
                        + f" at {slot_str}."
                    )
                    if _send_sms(phone, txt):
                        data[sms_flag] = True
                # --- Email ---
                email_addr = data.get("email")
                if email_addr and not data.get(email_flag):
                    if _send_email(email_addr, slot_str):
                        data[email_flag] = True

    _atomic_save(bookings)


# -----------------------------------------------------------------------------
# bootstrap called from receiver
# -----------------------------------------------------------------------------


def start_scheduler(app):
    sched = BackgroundScheduler()
    sched.add_job(check_reminders, "interval", minutes=1, id="reminders")
    sched.start()
    app.state._reminder_sched = sched
    print("🚀 Reminder scheduler running (checks every 60 s)")
