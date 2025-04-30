# tools/check_availability_tool.py
from datetime import datetime, timedelta
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from langchain.tools import StructuredTool
from handlers.booking_handler import slot_taken

from handlers.booking_handler import slot_taken  # we already created this


class CheckAvailInput(BaseModel):
    """Day and time the customer wants, e.g. 'Wednesday 3:30 PM'."""

    slot: str = Field(..., description="Desired day-time string")
    user_number: str


def _round_to_quarter(dt: datetime) -> datetime:
    minute = dt.minute
    qtr = (minute + 7) // 15 * 15
    if qtr == 60:
        dt += timedelta(hours=1)
        qtr = 0
    return dt.replace(minute=qtr, second=0, microsecond=0)


def find_next_free_slot(start_slot: str, *, max_checks: int = 16) -> str | None:
    """Return the nearest later 15-min slot that’s free, or None."""
    dt = datetime.strptime(start_slot, "%A %I:%M %p")
    for _ in range(max_checks):
        dt += timedelta(minutes=15)
        next_slot = dt.strftime("%A %-I:%M %p")
        if not slot_taken(next_slot):
            return next_slot
    return None


def check_availability(slot: str, user_number: str) -> str:
    """
    Return 'taken' if the slot is already booked by someone else,
    otherwise 'free'. The agent can then decide to book it or offer
    alternatives.
    """
    return "taken" if slot_taken(slot, exclude_user=user_number) else "free"


CheckAvailabilityTool = StructuredTool.from_function(
    func=check_availability,
    name="CheckAvailabilityTool",
    description="Checks if a proposed time slot is free or already booked. "
    "Returns 'free' or 'taken'.",
)

CheckAvailabilityTool = StructuredTool.from_function(
    func=check_availability,
    name="CheckAvailabilityTool",
    args_schema=CheckAvailInput,
    description=(
        "Check whether a specific appointment slot is free. "
        "Returns one of: 'available', 'taken', or 'nearest::<alternative slot>'."
    ),
)
