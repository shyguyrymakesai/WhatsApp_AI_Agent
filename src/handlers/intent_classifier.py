"""handlers/intent_classifier.py
Improved lightweight intent classifier for WhatsApp agent.
- broader vocabulary ("pencil", "slot", "midnight", "noon", etc.)
- recognises simple time expressions (e.g. "3pm", "14:30") so
  "tomorrow 3 pm" triggers BOOK_APPT
- distinguishes availability questions ("any slots Friday?") from
  booking commands
- keeps the dependency‑free philosophy: only `re` and `Enum`
"""

from __future__ import annotations

import re
from enum import Enum, auto


class Intent(Enum):
    LOOKUP_APPT = auto()  # “Do I already have something booked?”
    BOOK_APPT = auto()  # “Book me Friday at 2”
    CANCEL_APPT = auto()  # “Cancel my appointment”
    CHECK_DAY = auto()  # “Any slots on Friday?”
    SMALLTALK = auto()  # Greetings / thanks
    OTHER = auto()  # Fallback ─ pass to LLM


# ---------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------
WEEKDAY = r"monday|tuesday|wednesday|thursday|friday|saturday|sunday"
RELATIVE_DAY = r"today|tomorrow|tonight|next|upcoming"
TIME_HHMM = r"\d{1,2}(:\d{2})?\s*(?:am|pm)?"  # 3, 14:30, 7 pm, 9am
SPECIAL_TIME = r"midnight|noon"

_BOOK_RE = re.compile(
    rf"\b(book|reserve|schedule|appointment|appt|slot|pencil)\b", re.I
)
_CANCEL_RE = re.compile(r"\b(cancel|delete|drop|remove|clear)\b", re.I)
_DAY_RE = re.compile(rf"\b({WEEKDAY})\b", re.I)
_RELATIVE_RE = re.compile(rf"\b({RELATIVE_DAY})\b", re.I)
_TIME_RE = re.compile(rf"\b({TIME_HHMM}|{SPECIAL_TIME})\b", re.I)
_LOOKUP_RE = re.compile(r"\b(booked|scheduled|reserved|what time|when is)\b", re.I)

_SMALLTALK_SINGLE = {
    "hi",
    "hello",
    "hey",
    "thanks",
    "thank you",
    "yo",
    "sup",
    "howdy",
}

# quick lambda helpers -------------------------------------------------
_contains = lambda pat, msg: bool(pat.search(msg))


def classify_intent(message: str) -> Intent:
    """Return an Intent enum using keyword heuristics only."""

    msg = message.lower().strip()

    # 0 ─ small‑talk (single‑word/short greetings)
    if msg in _SMALLTALK_SINGLE:
        return Intent.SMALLTALK

    # 1 ─ cancel beats everything
    if _contains(_CANCEL_RE, msg):
        return Intent.CANCEL_APPT

    # 2 ─ explicit lookup of existing appointment
    if _contains(_LOOKUP_RE, msg) or (
        ("have" in msg or "currently" in msg)
        and ("appt" in msg or "appointment" in msg)
    ):
        return Intent.LOOKUP_APPT

    # 3 ─ availability question for a specific day
    if _contains(_DAY_RE, msg) and (
        "any" in msg or "available" in msg or "open" in msg or "slot" in msg
    ):
        return Intent.CHECK_DAY

    # 4 ─ booking intent:
    #     – contains booking verbs, OR
    #     – contains a day (weekday/relative) AND a time expression
    if (
        _contains(_BOOK_RE, msg)
        or (
            (_contains(_DAY_RE, msg) or _contains(_RELATIVE_RE, msg))
            and _contains(_TIME_RE, msg)
        )
        or (_contains(_TIME_RE, msg) and "pencil" in msg)
    ):
        return Intent.BOOK_APPT

    # 5 ─ fallback
    return Intent.OTHER
