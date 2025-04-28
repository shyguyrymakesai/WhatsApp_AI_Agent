# handlers/day_detector.py


def detect_day_request(message: str) -> str:
    """
    Detect if the user is asking about a specific day.
    """
    message = message.lower()
    days = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    for day in days:
        if day in message:
            return day
    return ""
