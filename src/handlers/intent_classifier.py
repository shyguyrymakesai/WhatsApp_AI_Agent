"""handlers/intent_classifier.py
Improved lightweight intent classifier for WhatsApp agent.
- broader vocabulary ("pencil", "slot", "midnight", "noon", etc.)
- recognizes simple time expressions (e.g. "3pm", "14:30") so
  "tomorrow 3 pm" triggers BOOK_APPT
- distinguishes availability questions ("any slots Friday?") from
  booking commands
- keeps the dependency-free philosophy: only `re` and `Enum`
"""

from __future__ import annotations

import re
from enum import Enum, auto


class Intent(Enum):
    RESCHEDULE_APPT = auto()
    LOOKUP_APPT = auto()
    BOOK_APPT = auto()
    CANCEL_APPT = auto()
    CHECK_DAY = auto()
    SMALLTALK = auto()
    OTHER = auto()


# ---------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------
RESCH_RE = re.compile(r"\b(reschedule|move|change|push back|pushback)\b", re.I)
BOOK_RE = re.compile(r"\b(book|reserve|schedule|appointment|appt|slot|pencil)\b", re.I)
CANCEL_RE = re.compile(r"\b(cancel|delete|drop|remove|clear)\b", re.I)
DAY_RE = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I
)
REL_RE = re.compile(r"\b(today|tomorrow|tonight|next|upcoming)\b", re.I)
TIME_RE = re.compile(r"\b(\d{1,2}(:\d{2})?\s*(?:am|pm)?|midnight|noon)\b", re.I)
LOOKUP_RE = re.compile(r"\b(booked|scheduled|reserved|what time|when is)\b", re.I)

SMALLTALK_SINGLE = {
    "hi",
    "hello",
    "hey",
    "thanks",
    "thank you",
    "yo",
    "sup",
    "howdy",
}

# helper to test regex
_contains = lambda pattern, text: bool(pattern.search(text))


def classify_intent(message: str) -> Intent:
    """Return an Intent enum using keyword heuristics only."""
    msg = message.lower().strip()

    # 1. reschedule requests
    if RESCH_RE.search(msg):
        return Intent.RESCHEDULE_APPT

    # 2. small-talk short greetings
    if msg in SMALLTALK_SINGLE:
        return Intent.SMALLTALK

    # 3. cancel intent
    if _contains(CANCEL_RE, msg):
        return Intent.CANCEL_APPT

    # 4. explicit lookup of existing appointment
    if _contains(LOOKUP_RE, msg) or (
        ("have" in msg or "currently" in msg)
        and ("appt" in msg or "appointment" in msg)
    ):
        return Intent.LOOKUP_APPT

    # 5. availability question for a specific day
    if _contains(DAY_RE, msg) and (
        "any" in msg or "available" in msg or "open" in msg or "slot" in msg
    ):
        return Intent.CHECK_DAY

    # 6. booking intent
    if (
        _contains(BOOK_RE, msg)
        or (
            (_contains(DAY_RE, msg) or _contains(REL_RE, msg))
            and _contains(TIME_RE, msg)
        )
        or (_contains(TIME_RE, msg) and "pencil" in msg)
    ):
        return Intent.BOOK_APPT

    # fallback
    return Intent.OTHER
