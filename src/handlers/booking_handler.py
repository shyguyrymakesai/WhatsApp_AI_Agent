import os
import json
import random
import re
from datetime import datetime, timedelta
from src.utils.whatsapp import send_whatsapp_message

BOOKINGS_FILE = "data/bookings.json"

# Configuration
WORKING_HOURS_START = 9  # 9AM
WORKING_HOURS_END = 17  # 5PM
SLOT_INTERVAL_MINUTES = 60
DAYS_AHEAD = 7


def load_bookings():
    if not os.path.exists(BOOKINGS_FILE):
        os.makedirs(os.path.dirname(BOOKINGS_FILE), exist_ok=True)
        with open(BOOKINGS_FILE, "w") as f:
            json.dump({}, f)
    with open(BOOKINGS_FILE, "r") as f:
        data = json.load(f)
    if isinstance(data, list):
        data = {}
        save_all_bookings(data)
    return data


def save_all_bookings(bookings: dict):
    with open(BOOKINGS_FILE, "w") as f:
        json.dump(bookings, f, indent=4)


def save_individual_booking(customer_id: str, selected_time: str):
    bookings = load_bookings()
    bookings[customer_id] = {
        "customer_id": customer_id,
        "time": selected_time,
        "reminder_sent": False,
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


def get_booking_options(desired_day: str = "", raw: bool = False) -> list[str] | str:
    """
    Get booking slots. If raw=True: return slot list. Else return formatted message.
    """
    all_slots = [
        ("monday", "11:00 AM"),
        ("monday", "12:00 PM"),
        ("monday", "1:00 PM"),
        ("tuesday", "9:00 AM"),
        ("tuesday", "10:00 AM"),
        ("tuesday", "11:00 AM"),
        ("wednesday", "9:00 AM"),
        ("wednesday", "10:00 AM"),
        ("thursday", "9:00 AM"),
        ("thursday", "10:00 AM"),
        ("friday", "9:00 AM"),
        ("friday", "10:00 AM"),
        ("saturday", "9:00 AM"),
        ("saturday", "10:00 AM"),
        ("saturday", "11:00 AM"),
        ("sunday", "1:00 PM"),
        ("sunday", "2:00 PM"),
    ]

    if desired_day:
        filtered = [
            f"{day.title()} {time}"
            for day, time in all_slots
            if desired_day.lower() in day.lower()
        ]
    else:
        filtered = [f"{day.title()} {time}" for day, time in all_slots]

    if not filtered:
        return "⚠️ No available slots for the day you requested." if not raw else []

    random.shuffle(filtered)
    limited = filtered[:5]

    if raw:
        return limited

    message = "🔎 Available times:\n"
    for idx, slot in enumerate(limited, start=1):
        message += f"{idx}. {slot}\n"
    return message.strip()


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
