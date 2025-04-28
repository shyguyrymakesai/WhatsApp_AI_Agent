import os
import json
from datetime import datetime, timedelta

BOOKINGS_FILE = "data/bookings.json"

# Configuration
WORKING_HOURS_START = 9  # 9AM
WORKING_HOURS_END = 17  # 5PM
SLOT_INTERVAL_MINUTES = 60
DAYS_AHEAD = 7

# booking_handler.py

import json
import os

BOOKINGS_FILE = "bookings.json"


def load_bookings():
    """
    Load bookings from file, or create an empty one if missing.
    """
    if not os.path.exists(BOOKINGS_FILE):
        with open(BOOKINGS_FILE, "w") as f:
            json.dump({}, f)

    with open(BOOKINGS_FILE, "r") as f:
        return json.load(f)


def save_bookings(bookings):
    """
    Save bookings back to the file.
    """
    with open(BOOKINGS_FILE, "w") as f:
        json.dump(bookings, f, indent=4)


def is_waiting_for_booking(user_number: str) -> bool:
    """
    Check if a user is currently expected to pick a booking option.
    """
    bookings = load_bookings()
    return bookings.get(user_number, {}).get("waiting_for_booking", False)


def set_waiting_for_booking(user_number: str, waiting: bool):
    """
    Update if user is waiting for a booking option.
    """
    bookings = load_bookings()
    if user_number not in bookings:
        bookings[user_number] = {}

    bookings[user_number]["waiting_for_booking"] = waiting
    save_bookings(bookings)


def is_waiting_for_booking(user_number: str, bookings: dict) -> bool:
    """
    Checks if the user was recently shown booking options but hasn't picked yet.
    """
    return bookings.get(user_number, {}).get("awaiting_selection", False)


def set_waiting_for_booking(user_number: str, bookings: dict, waiting: bool):
    """
    Update whether the user is expected to pick a booking slot.
    """
    if user_number not in bookings:
        bookings[user_number] = {}
    bookings[user_number]["awaiting_selection"] = waiting


def initialize_bookings_file():
    dir_name = os.path.dirname(BOOKINGS_FILE)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    if not os.path.exists(BOOKINGS_FILE):
        with open(BOOKINGS_FILE, "w") as f:
            f.write("[]")  # or whatever your default contents should be


def detect_booking_intent(message):
    keywords = ["book", "appointment", "schedule"]
    return any(keyword in message.lower() for keyword in keywords)


def detect_cancel_intent(message: str) -> bool:
    """
    Only treat direct cancel words as cancel intent.
    """
    message = message.lower()
    return any(
        word in message for word in ["cancel", "delete", "remove", "cancellation"]
    )


def generate_upcoming_slots():
    slots = []
    now = datetime.now()

    for i in range(DAYS_AHEAD):
        day = now + timedelta(days=i)
        day_name = day.strftime("%A")

        for hour in range(WORKING_HOURS_START, WORKING_HOURS_END):
            slot_time = day.replace(hour=hour, minute=0, second=0, microsecond=0)
            if slot_time > now:
                time_formatted = slot_time.strftime("%I:%M %p").lstrip("0")
                slots.append(f"{day_name} {time_formatted}")

    return slots


def get_booking_options():
    with open(BOOKINGS_FILE, "r") as f:
        bookings = json.load(f)

    booked_times = {booking["time"] for booking in bookings.values()}
    upcoming_slots = generate_upcoming_slots()
    available_slots = [slot for slot in upcoming_slots if slot not in booked_times]

    offer_slots = available_slots[:3]

    if not offer_slots:
        return "Sorry, no available appointment times right now."

    options = "I'd love to help! Please choose a time:\n"
    for idx, slot in enumerate(offer_slots, start=1):
        options += f"🕒 {idx}) {slot}\n"
    options += "(Reply with the number!)"

    return options


def save_booking(customer_id, selected_time):
    with open(BOOKINGS_FILE, "r") as f:
        bookings = json.load(f)

    appointment_datetime = datetime.strptime(selected_time, "%A %I:%M %p")
    reminder_time = appointment_datetime - timedelta(days=1)

    bookings[customer_id] = {
        "customer_id": customer_id,
        "time": selected_time,
        "reminder_time": reminder_time.strftime("%A %I:%M %p"),
        "reminder_sent": False,
    }

    with open(BOOKINGS_FILE, "w") as f:
        json.dump(bookings, f, indent=4)


def handle_booking_response(customer_id, message):
    with open(BOOKINGS_FILE, "r") as f:
        bookings = json.load(f)

    booked_times = {booking["time"] for booking in bookings.values()}
    upcoming_slots = generate_upcoming_slots()
    available_slots = [slot for slot in upcoming_slots if slot not in booked_times]

    try:
        selection = int(message.strip()) - 1
        selected_time = available_slots[selection]
    except (ValueError, IndexError):
        return "Sorry, I didn't understand that. Please reply with the number of the time you'd like!"

    save_booking(customer_id, selected_time)

    return (
        f"Awesome! You're booked for {selected_time}. We'll remind you 24 hours before!"
    )


def cancel_booking(customer_id):
    with open(BOOKINGS_FILE, "r") as f:
        bookings = json.load(f)

    if customer_id in bookings:
        del bookings[customer_id]
        with open(BOOKINGS_FILE, "w") as f:
            json.dump(bookings, f, indent=4)
        return True
    return False


def is_valid_booking_option(message):
    return message.isdigit() and 1 <= int(message) <= 3
