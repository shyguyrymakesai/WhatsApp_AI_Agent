# src/utils/time_utils.py


def detect_weekday_in_message(message: str) -> bool:
    weekdays = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    message = message.lower()
    return any(day in message for day in weekdays)


def extract_weekday_from_message(message: str) -> str | None:
    weekdays = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    message = message.lower()
    for day in weekdays:
        if day in message:
            return day.capitalize()
    return None
