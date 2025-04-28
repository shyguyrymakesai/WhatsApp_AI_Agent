# tools/booking_tool.py
from langchain.tools import StructuredTool
from handlers.booking_handler import get_booking_options, save_individual_booking
from src.utils.whatsapp import send_whatsapp_message


def book_appointment(number: str, day: str = None, time: str = None) -> str:
    """
    Book a client into an appointment. If an exact time is given, match it if available.
    Otherwise, show available slots for the requested day.
    """
    options = get_booking_options(desired_day=day)

    if not options:
        send_whatsapp_message(number, "😞 Sorry, no slots are available for that day.")
        return "No slots available"

    if time:
        for option in options.split("\n"):
            if time in option:
                selected_time = option.split(") ")[1]
                save_individual_booking(number, selected_time)
                send_whatsapp_message(number, f"✅ Booked for {selected_time}!")
                return "Booked preferred time"

    send_whatsapp_message(number, f"🔎 Here are available times:\n{options}")
    return "Offered available slots"


# Export it as a StructuredTool
BookingTool = StructuredTool.from_function(
    func=book_appointment,
    name="BookingTool",
    description="Book an appointment based on a client's preferred day and/or time.",
)
