"""LangChain tool that reports whether a requested appointment slot is free."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from src.handlers.booking_handler import load_bookings, slot_taken


class CheckAvailInput(BaseModel):
    """Input schema used by :data:`CheckAvailabilityTool`."""

    slot: str = Field(
        ..., description="Desired slot formatted as 'Wednesday 3:30 PM'."
    )
    user_number: str = Field(
        ..., description="Caller phone number (used to ignore their own booking)."
    )


def _nearest_free_slot(
    start: datetime, bookings: dict, *, max_checks: int = 16
) -> Optional[str]:
    """Return the first untaken 15-minute slot after ``start``.

    ``max_checks`` bounds the search to roughly four hours.
    """

    step = timedelta(minutes=15)
    dt = start
    for _ in range(max_checks):
        dt += step
        candidate = dt.strftime("%A %I:%M %p").replace(" 0", " ")
        if not slot_taken(candidate, bookings):
            return candidate
    return None


def check_availability(slot: str, user_number: str) -> str:
    """Check whether *slot* is free for booking."""

    bookings = load_bookings()
    try:
        requested_dt = datetime.strptime(slot, "%A %I:%M %p")
    except ValueError:
        return "taken"

    if not slot_taken(slot, bookings, exclude_user=user_number):
        return "available"

    alternative = _nearest_free_slot(requested_dt, bookings)
    if alternative and not slot_taken(alternative, bookings):
        return f"nearest::{alternative}"

    return "taken"


CheckAvailabilityTool = StructuredTool.from_function(
    func=check_availability,
    name="CheckAvailabilityTool",
    args_schema=CheckAvailInput,
    description=(
        "Report whether a given appointment slot is available. "
        "Returns 'available', 'taken', or 'nearest::<alternative>'."
    ),
)
