from handlers import reminder_handler, booking_handler, question_handler
from src.utils.whatsapp import send_whatsapp_message


def parse_user_message(message: str) -> str:
    """
    Very simple rule-based intent parser for now.
    """
    lowered = message.lower()
    if "remind me" in lowered or "reminder" in lowered:
        return "reminder"
    elif "book" in lowered or "meeting" in lowered:
        return "booking"
    elif "question" in lowered or "ask" in lowered:
        return "question"
    else:
        return "unknown"


def route_message(phone_number: str, message: str):
    """
    Parse the user message and route to the correct handler.
    """
    intent = parse_user_message(message)

    if intent == "reminder":
        reminder_handler.handle_reminder(phone_number, message)
    elif intent == "booking":
        booking_handler.handle_booking(phone_number, message)
    elif intent == "question":
        question_handler.handle_question(phone_number, message)
    else:
        send_whatsapp_message(
            phone_number,
            "❓ Sorry, I didn’t understand that. Try asking to set a reminder, book something, or ask a question!",
        )
