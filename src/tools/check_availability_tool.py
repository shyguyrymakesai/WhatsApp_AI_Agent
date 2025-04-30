# tools/check_availability_tool.py
"""Check whether a specific appointment slot is available.

The tool answers the agent with **one** of three tokens so the agent can
react appropriately:

* ``"available"`` – nobody has booked that slot yet.
* ``"taken"`` – the slot is already occupied **and** no close alternative
  was found.
* ``"nearest::<alternative slot>"`` – the requested slot is taken, but the
  next free 15‑minute slot (within the next four hours) is returned so the
  agent can offer it.

The function is wrapped as a LangChain ``StructuredTool`` so the agent can
call it with JSON‑serialisable arguments.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from src.handlers.booking_handler import slot_taken  # ← uses shared booking store

# ----------------------------------------------------------------------------
# Pydantic schema – guarantees the agent passes the two required fields
# ----------------------------------------------------------------------------


class CheckAvailInput(BaseModel):
    """Input expected by ``CheckAvailabilityTool``."""

    slot: str = Field(
        ...,
        description="Desired day‑time string, e.g. 'Wednesday 3:30 PM'",
    )
    user_number: str = Field(
        ..., description="Caller phone number (for self‑exclusion)"
    )


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _nearest_free_slot(start: datetime, *, max_checks: int = 16) -> Optional[str]:
    """Return the first un‑taken 15‑min slot *after* ``start``.

    *Checks up to ``max_checks``* intervals (default ≈ 4 hours). ``None`` if
    everything is occupied.
    """
    step = timedelta(minutes=15)
    dt = start
    for _ in range(max_checks):
        dt += step
        candidate = dt.strftime("%A %-I:%M %p")
        if not slot_taken(candidate):
            return candidate
    return None


# ----------------------------------------------------------------------------
# Core tool function
# ----------------------------------------------------------------------------


def check_availability(slot: str, user_number: str) -> str:
    """Check whether *slot* is free.

    The caller (agent) *may* be the same user who already holds the slot, so
    we exclude ``user_number`` when checking collisions.
    """
    # Normalise – allow things like "3:30 pm Wednesday" (robustness helper)
    try:
        dt_req = datetime.strptime(slot, "%A %I:%M %p")
    except ValueError:
        # Agent passed something odd – fail closed
        return "taken"

    # 1️⃣ Direct hit
    if not slot_taken(slot, exclude_user=user_number):
        return "available"

    # 2️⃣ Suggest the next nearest free slot (within ~4 hours)
    alt = _nearest_free_slot(dt_req)
    return f"nearest::{alt}" if alt else "taken"


# ----------------------------------------------------------------------------
# LangChain wrapper
# ----------------------------------------------------------------------------

CheckAvailabilityTool = StructuredTool.from_function(
    func=check_availability,
    name="CheckAvailabilityTool",
    args_schema=CheckAvailInput,
    description=(
        "Report whether a given appointment slot is available. "
        "Returns one of: 'available', 'taken', or 'nearest::<alternative>'."
    ),
)
