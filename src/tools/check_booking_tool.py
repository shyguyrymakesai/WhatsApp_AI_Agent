from langchain.tools import StructuredTool
from pydantic import BaseModel
from handlers.booking_handler import get_user_booking


class CheckBookingInput(BaseModel):
    user_number: str  # WhatsApp JID


def check_booking(user_number: str) -> str:
    slot = get_user_booking(user_number)
    if slot:
        return f"📅 You are booked for {slot}!"
    return "😔 I couldn’t find an active booking for you."


CheckBookingTool = StructuredTool.from_function(
    func=check_booking,
    name="CheckBookingTool",
    args_schema=CheckBookingInput,
    description="Lookup whether the given user already has an appointment.",
)
