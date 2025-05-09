import os
import json
import random
import re
from datetime import datetime, timedelta
from src.utils.whatsapp import send_whatsapp_message
import tempfile, shutil
from utils.slot_parser import parse_slot
from typing import Any

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # adjust depth if needed
BOOKINGS_FILE = BASE_DIR / "data" / "bookings.json"
BOOKINGS_FILE.parent.mkdir(parents=True, exist_ok=True)


# Configuration
WORKING_HOURS_START = 9  # 9AM
WORKING_HOURS_END = 17  # 5PM
SLOT_INTERVAL_MINUTES = 15
DAYS_AHEAD = 7


def load_bookings():
    if not os.path.exists(BOOKINGS_FILE):
        os.makedirs(os.path.dirname(BOOKINGS_FILE), exist_ok=True)
        with open(BOOKINGS_FILE, "w") as f:
            json.dump({}, f)
    with open(BOOKINGS_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}
            save_all_bookings(data)
    if isinstance(data, list):
        data = {}
        save_all_bookings(data)
    return data


def save_all_bookings(bookings: dict):
    tmp_fd, tmp_path = tempfile.mkstemp(dir=BOOKINGS_FILE.parent, suffix=".tmp")
    with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
        json.dump(bookings, f, indent=4)
        f.flush()
        os.fsync(f.fileno())  # guarantee bytes hit disk
    shutil.move(tmp_path, BOOKINGS_FILE)


BASE_DIR = Path(__file__).resolve().parents[2]
BOOKINGS_FILE = BASE_DIR / "data" / "bookings.json"


def load_bookings() -> dict[str, Any]:
    BOOKINGS_FILE.parent.mkdir(exist_ok=True, parents=True)
    if not BOOKINGS_FILE.exists():
        BOOKINGS_FILE.write_text("{}")
    try:
        return json.loads(BOOKINGS_FILE.read_text())
    except json.JSONDecodeError:
        return {}


def save_all_bookings(bookings: dict[str, Any]) -> None:
    fd, tmp = tempfile.mkstemp(dir=BOOKINGS_FILE.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(bookings, f, indent=2)
    shutil.move(tmp, BOOKINGS_FILE)


def slot_taken(
    slot: str,
    bookings: dict[str, Any] | None = None,
    exclude_user: str | None = None,
) -> bool:
    """Return True if this slot is already booked by someone else."""
    if bookings is None:
        bookings = load_bookings()
    canon = parse_slot(slot) or slot
    for user, data in bookings.items():
        if user == exclude_user:
            continue
        booked = data.get("time")
        if not booked:
            continue
        if (parse_slot(booked) or booked) == canon:
            return True
    return False


def save_individual_booking(
    user_number: str,
    slot: str,
    email: str | None = None,
) -> None:
    """Atomically load, check, save a new booking."""
    bookings = load_bookings()
    # collision check
    if slot_taken(slot, bookings, exclude_user=user_number):
        raise ValueError("Slot already booked")

    # write the booking
    bookings[user_number] = {
        "time": slot,
        "email": email or bookings.get(user_number, {}).get("email"),
        "awaiting_selection": False,
        "reminder_sent_sms": False,
        "reminder_sent_email": False,
    }
    save_all_bookings(bookings)


def initialize_bookings_file():
    load_bookings()


def detect_booking_intent(message: str) -> bool:
    keywords = [
        "book",
        "booking",
        "appointment",
        "schedule",
        "reserve",
        "meet",
        "meeting",
    ]
    return any(keyword in message.lower() for keyword in keywords)


def detect_cancel_intent(message: str) -> bool:
    return any(
        word in message.lower()
        for word in ["cancel", "delete", "remove", "cancellation"]
    )


def generate_upcoming_slots():
    slots = []
    now = datetime.now()
    for i in range(DAYS_AHEAD):
        day = now + timedelta(days=i)
        for hour in range(WORKING_HOURS_START, WORKING_HOURS_END):
            slot_time = day.replace(hour=hour, minute=0, second=0, microsecond=0)
            if slot_time > now:
                slots.append(slot_time.strftime("%A %m/%d %I:%M %p").lstrip("0"))
    return slots


def get_user_booking(customer_id: str) -> str | None:
    bookings = load_bookings()
    booking = bookings.get(customer_id)
    if booking and "time" in booking:
        return booking["time"]
    return None


def _quarter_hour_range(start_h, end_h):
    for h in range(start_h, end_h):
        for m in (0, 15, 30, 45):
            yield h, m


import random


# helper used earlier
def _quarter_hour_range(start_h, end_h):
    for h in range(start_h, end_h):
        for m in (0, 15, 30, 45):
            yield h, m


def get_booking_options(desired_day: str = "", raw: bool = False, limit: int = 5):
    """Return a list of slots or a pretty menu message."""
    weekdays = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    # Build every 15-minute slot in working hours
    all_slots = [
        (day, f"{hour%12 or 12}:{minute:02d} {'AM' if hour < 12 else 'PM'}")
        for day in weekdays
        for hour, minute in _quarter_hour_range(WORKING_HOURS_START, WORKING_HOURS_END)
    ]

    # Filter by requested day (if any)
    if desired_day:
        filtered = [
            f"{d.title()} {t}" for d, t in all_slots if desired_day.lower() in d.lower()
        ]
    else:
        filtered = [f"{d.title()} {t}" for d, t in all_slots]

    # No matches → return safe empty value
    if not filtered:
        return [] if raw else "⚠️ No available slots for the day you requested."

    random.shuffle(filtered)
    limited = filtered[:limit]

    if raw:
        return limited

    message = "🔎 Available times:\n" + "\n".join(
        f"{idx+1}. {slot}" for idx, slot in enumerate(limited)
    )
    return message


def is_waiting_for_booking(user_number: str, bookings: dict) -> bool:
    return bookings.get(user_number, {}).get("awaiting_selection", False)


def set_waiting_for_booking(user_number: str, bookings: dict, waiting: bool):
    if user_number not in bookings:
        bookings[user_number] = {}
    bookings[user_number]["awaiting_selection"] = waiting


def handle_booking_response(
    user_number: str, user_message: str, shown_slots: dict
) -> str:
    match = re.search(r"\b(\d+)\b", user_message)
    if not match:
        return (
            "⚠️ Invalid selection. Please reply with the number of the time you'd like."
        )

    selection = int(match.group(1))

    slots = shown_slots.get(user_number, [])
    if not slots or selection < 1 or selection > len(slots):
        return "⚠️ Invalid selection. Please reply with a valid number from the list."

    chosen_slot = slots[selection - 1]

    bookings = load_bookings()
    bookings[user_number] = {
        "time": chosen_slot,
        "reminder_time": None,
    }
    save_all_bookings(bookings)

    if user_number in shown_slots:
        del shown_slots[user_number]

    return f"✅ Awesome! You're booked for {chosen_slot}. We'll remind you 24 hours before!"


def cancel_booking(customer_id: str):
    bookings = load_bookings()
    if customer_id in bookings:
        del bookings[customer_id]
        save_all_bookings(bookings)
        return True
    return False


def count_current_booking_options() -> int:
    options_message = get_booking_options()
    return options_message.count("🕒")


def is_valid_booking_option(message: str) -> bool:
    match = re.search(r"\b(\d+)\b", message)
    if not match:
        return False

    max_option = count_current_booking_options()
    selection = int(match.group(1))

    return 1 <= selection <= max_option


def handle_booking(phone_number: str, message: str, shown_slots: dict):
    bookings = load_bookings()
    if detect_cancel_intent(message):
        success = cancel_booking(phone_number)
        send_whatsapp_message(
            phone_number,
            (
                "✅ Your booking has been canceled!"
                if success
                else "⚠️ You don't have any bookings to cancel."
            ),
        )
    elif is_waiting_for_booking(phone_number, bookings):
        response = handle_booking_response(phone_number, message, shown_slots)
        set_waiting_for_booking(phone_number, bookings, False)
        save_all_bookings(bookings)
        send_whatsapp_message(phone_number, response)
    else:
        options_list = get_booking_options(raw=True)
        shown_slots[phone_number] = options_list
        formatted_message = "🔎 Available times:\n" + "\n".join(
            f"{idx+1}. {slot}" for idx, slot in enumerate(options_list)
        )
        set_waiting_for_booking(phone_number, bookings, True)
        save_all_bookings(bookings)
        send_whatsapp_message(phone_number, formatted_message)
