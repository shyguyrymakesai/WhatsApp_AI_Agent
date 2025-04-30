import re


def handle_booking_reply(user_message: str, available_slots: list) -> dict:
    """
    Parse a user reply during booking and return a structured action.

    Returns
    -------
    dict
        * {"action": "book", "selected_slot": "<slot>"} – user picked a slot
        * {"action": "ask_new_day"}                    – user wants a different day/time
        * {"action": "unknown"}                        – couldn’t understand
    """
    msg = user_message.lower().strip()

    # Asking for a different day / time
    if msg in {
        "different day",
        "another day",
        "other day",
        "new day",
        "different time",
        "different",
    }:
        return {"action": "ask_new_day"}

    # Grab the first digit anywhere in the string (e.g., "1", "option 2", "2 please")
    match = re.search(r"\b(\d+)\b", msg)
    if match:
        idx = int(match.group(1)) - 1
        if 0 <= idx < len(available_slots):
            return {"action": "book", "selected_slot": available_slots[idx]}

    return {"action": "unknown"}
