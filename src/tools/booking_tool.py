import re
from typing import Optional

from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from src.handlers.booking_handler import get_booking_options, save_individual_booking
from src.tools.check_availability_tool import check_availability
from src.utils.slot_parser import parse_slot


class BookingInput(BaseModel):
    """Input schema for the BookingTool."""

    number: str = Field(..., description="User phone number (including @c.us suffix)")
    user_message: Optional[str] = Field(
        None, description="User message to interpret for booking or selection"
    )
    day: Optional[str] = Field(
        None, description="Optional day filter for listing slots"
    )


def book_appointment(
    number: str, user_message: Optional[str] = None, day: Optional[str] = None
) -> str:
    """
    Handle booking conversation:
      - If user_message is empty: return 'offer::<newline-list>' with available slots.
      - If numeric selection: book that indexed slot.
      - If natural-language time: parse and attempt to book or suggest nearest.
      - If neither: ask for day/time.
    """
    # 1️⃣ Load current options
    raw = get_booking_options(desired_day=day)
    options = [line.strip() for line in raw.split("\n") if re.match(r"^\s*\d", line)]
    slots = [re.sub(r"^\s*\d+\.?\s*", "", s) for s in options]

    # 2️⃣ First-contact: show menu
    if not user_message:
        menu = "\n".join(f"{i+1}. {slot}" for i, slot in enumerate(slots))
        return f"offer::{menu}"

    text = user_message.strip()

    # 3️⃣ Numeric selection
    if re.fullmatch(r"[1-9]\d*", text):
        idx = int(text) - 1
        if 0 <= idx < len(slots):
            chosen = slots[idx]
            try:
                save_individual_booking(number, chosen)
                return f"booked::{chosen}"
            except ValueError:
                return "slot_taken"

    # 4️⃣ Natural-language parsing
    natural = parse_slot(text)
    if natural:
        avail = check_availability(natural, user_number=number)
        if avail == "available":
            save_individual_booking(number, natural)
            return f"booked::{natural}"
        if avail.startswith("nearest::"):
            # suggest alternative
            alt = avail.split("::", 1)[1]
            return f"nearest::{alt}"
        return "slot_taken"

    # 5️⃣ Fallback: ask explicitly
    return "ask_day"


# Wrap as a StructuredTool for LangChain agents
BookingTool = StructuredTool.from_function(
    func=book_appointment,
    name="BookingTool",
    args_schema=BookingInput,
    description=(
        "Handles appointment bookings, interprets natural-language times and numeric selections, "
        "and suggests nearest available slots when requested time is taken."
    ),
)
