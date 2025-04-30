# tools/booking_tool.py
import re
from datetime import timedelta, datetime

import dateparser
from langchain.tools import StructuredTool

from handlers.booking_handler import (
    get_booking_options,
    save_individual_booking,
    slot_taken,  # new helper we added earlier
)
from src.utils.smart_reply_handler import handle_booking_reply


# ----------------------------------------------------------------------
# Helper ─ parse “next Friday at 3”, “Sat 10 am”, etc.
# ----------------------------------------------------------------------


_WEEKDAYS = r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
_RELATIVE = r"(tomorrow|today|tonight)"

_COMPACT = re.compile(
    r"\b(?P<day>monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"tomorrow|today|tonight)\b"
    r"(?:\s+at)?\s+"
    r"(?P<hour>\d{1,2})"
    r"(?:[:\.]?(?P<minute>[0-5]\d))?"
    r"\s*(?P<ampm>am|pm)?\b",
    re.I,
)


def _round_to_quarter(dt: datetime) -> datetime:
    minute = (dt.minute + 7) // 15 * 15
    if minute == 60:
        dt += timedelta(hours=1)
        minute = 0
    return dt.replace(minute=minute, second=0, microsecond=0)


def _next_weekday(start: datetime, weekday_name: str) -> datetime:
    while start.strftime("%A").lower() != weekday_name:
        start += timedelta(days=1)
    return start


_WEEKDAYS = r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
_RELATIVE = r"(tomorrow|today|tonight)"

_COMPACT = re.compile(
    r"\b(?P<day>monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"tomorrow|today|tonight)\b"
    r"(?:\s+at)?\s+"
    r"(?:(?P<special>midnight|noon)|"
    r"(?P<hour>\d{1,2})(?:[:\.]?(?P<minute>[0-5]\d))?\s*(?P<ampm>am|pm)?)\b",
    re.I,
)


def _round_to_quarter(dt: datetime) -> datetime:
    minute = (dt.minute + 7) // 15 * 15
    if minute == 60:
        dt += timedelta(hours=1)
        minute = 0
    return dt.replace(minute=minute, second=0, microsecond=0)


def _next_weekday(start: datetime, weekday_name: str) -> datetime:
    """Advance to the next requested weekday name (e.g. "wednesday")."""
    while start.strftime("%A").lower() != weekday_name:
        start += timedelta(days=1)
    return start


def _parse_natural_slot(text: str) -> str | None:
    """Parse phrases like 'tomorrow at noon', 'Friday midnight', 'wed 3:45pm'.
    Returns canonical slot string (e.g. 'Friday 12:00 PM') or None.
    """
    print("🛠️  DEBUG _parse_natural_slot received:", text)
    text = text.lower()

    if re.search(r"\b(midnight|noon)\b", text) and not re.search(r"\d", text):
        # default day: 'tomorrow' if midnight is already past for today
        now = datetime.now()
        dt = now.replace(
            hour=0 if "midnight" in text else 12, minute=0, second=0, microsecond=0
        )
        if "midnight" in text and now >= dt:
            dt += timedelta(days=1)  # next day's midnight
        # proceed to rounding & slot creation at the end of the function

    m = _COMPACT.search(text)
    if m:
        day_token = m.group("day")

        # --- special words noon / midnight ----------------------------
        if m.group("special"):
            if m.group("special").lower() == "midnight":
                hour, minute = 0, 0  # 12 AM
            else:  # noon
                hour, minute = 12, 0  # 12 PM
        else:
            hour = int(m.group("hour"))
            minute = int(m.group("minute") or 0)
            ampm = (m.group("ampm") or "").lower()
            if not ampm:  # infer am/pm if missing
                ampm = "pm" if 1 <= hour <= 7 else "am"
            hour = hour % 12 + (12 if ampm == "pm" else 0)

        now = datetime.now().replace(second=0, microsecond=0)
        dt = _round_to_quarter(now.replace(hour=hour, minute=minute))

        # apply day component ------------------------------------------
        if day_token in ("tomorrow", "today", "tonight"):
            if day_token == "tomorrow" or (day_token == "tonight" and dt < now):
                dt += timedelta(days=1)
        else:
            dt = _next_weekday(dt, day_token)

    else:
        # fallback: use dateparser only when day+digit present ------------
        if not (
            re.search(rf"\b({_WEEKDAYS}|{_RELATIVE})\b", text)
            and re.search(r"\d", text)
        ):
            return None
        dt = dateparser.parse(
            text,
            settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
        )
        if not dt:
            return None
        dt = _round_to_quarter(dt)

    weekday = dt.strftime("%A")
    time_str = dt.strftime("%I:%M %p").lstrip("0")
    slot = f"{weekday} {time_str}"
    print("🛠️  DEBUG parsed slot →", slot)
    return slot


# ----------------------------------------------------------------------
# Main booking function
# ----------------------------------------------------------------------
def book_appointment(
    number: str, user_message: str | None = None, day: str | None = None
) -> str:
    """
    Handle booking dialog.

    Returns tokens for receiver/agent:
      * offer::<newline-list>   → show slots
      * ask_day                 → need a weekday
      * booked::<slot>          → success
      * slot_taken              → collision
      * no_slots / unrecognized → fallback
    """
    options = get_booking_options(desired_day=day)
    if not options:
        return "no_slots"

    available_slots = [
        re.sub(r"^\\s*\\d+\\s*[.)]\\s*", "", line).strip()
        for line in options.split("\\n")
        if re.match(r"^\\s*\\d", line)
    ]

    # ------------------------------------------------------------------ user reply path
    if user_message:
        # 1️⃣ Handle numeric replies & “different day”
        decision = handle_booking_reply(user_message, available_slots)

        if decision["action"] == "book":
            selected = decision["selected_slot"]
            try:
                save_individual_booking(number, selected)
                return f"booked::{selected}"
            except ValueError:
                return "slot_taken"

        if decision["action"] == "ask_new_day":
            return "ask_day"

        # 2️⃣ Natural-language date/time
        natural = _parse_natural_slot(user_message)
        if natural:
            if slot_taken(natural, exclude_user=number):
                return "slot_taken"
            save_individual_booking(number, natural)
            return f"booked::{natural}"

        return "unrecognized"

    # ------------------------------------------------------------------ first contact → menu
    return f"offer::{options}"


# ----------------------------------------------------------------------
# Wrap as a LangChain StructuredTool
# ----------------------------------------------------------------------
BookingTool = StructuredTool.from_function(
    func=book_appointment,
    name="BookingTool",
    description="Books appointments, responds to slot selections, "
    "and understands natural-language times like 'next Friday at 3'.",
)
