from __future__ import annotations

import re
from datetime import datetime, timedelta
import dateparser
import requests

# —— synonyms & patterns —————————————————————————————————————————————

# full & abbreviated weekdays
_WEEKDAYS = (
    r"monday|mon|tuesday|tue(?:s)?|wednesday|wed|thursday|thu(?:rs)?|"
    r"friday|fri|saturday|sat|sunday|sun"
)

# relative days
_RELATIVE = (
    r"today|tonight|tomorrow|tom|tmr|tmrw|" r"next(?:\s+wk|week)|day\s+after\s+tmr"
)

# special times
_SPECIAL = r"noon|midday|midnight"

# compact: [day] at? [hh][:mm]? ?(am|pm)?
_COMPACT = re.compile(
    rf"\b(?P<day>{_WEEKDAYS}|{_RELATIVE})\b"  # day token
    r"(?:\s+at)?\s+"
    rf"(?:(?P<special>{_SPECIAL})|"
    r"(?P<hour>\d{1,2})(?:[:\.]?(?P<minute>[0-5]\d))?\s*(?P<ampm>am|pm)?)\b",
    re.I,
)

# loose time for bare times without day
_TIME_ONLY = re.compile(
    r"\b(?P<h>\d{1,2})(?:[:\.]?(?P<m>[0-5]\d))?\s*(?P<ap>am|pm)?\b", re.I
)

# —— rounding & helpers ————————————————————————————————————————————


def _round_to_quarter(dt: datetime) -> datetime:
    minute = (dt.minute + 7) // 15 * 15
    if minute == 60:
        dt += timedelta(hours=1)
        minute = 0
    return dt.replace(minute=minute, second=0, microsecond=0)


def _next_weekday(start: datetime, wday: str) -> datetime:
    """Advance to the next given weekday name."""
    target = wday.lower()
    # normalize common abbreviations
    full = {
        "mon": "monday",
        "tue": "tuesday",
        "wed": "wednesday",
        "thu": "thursday",
        "thur": "thursday",
        "fri": "friday",
        "sat": "saturday",
        "sun": "sunday",
    }
    if target in full:
        target = full[target]
    while start.strftime("%A").lower() != target:
        start += timedelta(days=1)
    return start


# —— custom regex + dateparser parser ———————————————————————————————————


def _parse_custom(text: str) -> datetime | None:
    """
    Return a datetime if we can parse via compact regex or dateparser fallback,
    else None.
    """
    now = datetime.now().replace(second=0, microsecond=0)
    t = text.strip().lower()

    # 1) special tokens with no digits
    if re.search(rf"\b(?:noon|midday|midnight)\b", t) and not re.search(r"\d", t):
        hour = 12 if "noon" in t or "midday" in t else 0
        dt = now.replace(hour=hour, minute=0)
        if "midnight" in t and now >= dt:
            dt += timedelta(days=1)
        return _round_to_quarter(dt)

    # 2) day + time via compact regex
    m = _COMPACT.search(t)
    if m:
        day_tok = m.group("day")
        # determine hour/minute
        if m.group("special"):
            if m.group("special").lower() in ("noon", "midday"):
                hour, minute = 12, 0
            else:  # midnight
                hour, minute = 0, 0
        else:
            hour = int(m.group("hour"))
            minute = int(m.group("minute") or 0)
            ap = (m.group("ampm") or "").lower()
            if not ap:
                ap = "pm" if 1 <= hour <= 7 else "am"
            hour = hour % 12 + (12 if ap == "pm" else 0)

        dt = now.replace(hour=hour, minute=minute)
        dt = _round_to_quarter(dt)

        # apply day advance
        if day_tok in ("today", "tonight"):
            if day_tok == "tonight" and dt < now:
                dt += timedelta(days=1)
        elif day_tok in ("tomorrow", "tom", "tmr", "tmrw", "day after tmr"):
            dt += timedelta(days=1)
            if "day after" in day_tok:
                dt += timedelta(days=1)
        elif day_tok.startswith("next"):
            # “next week” → +7 days then same weekday
            dt = _next_weekday(dt + timedelta(days=7), dt.strftime("%A"))
        else:
            dt = _next_weekday(dt, day_tok)

        return dt

    # 3) fallback: weekday/relative + digits → dateparser
    if re.search(rf"\b({_WEEKDAYS}|{_RELATIVE})\b", t) and re.search(r"\d", t):
        parsed = dateparser.parse(t, settings={"PREFER_DATES_FROM": "future"})
        if parsed:
            return _round_to_quarter(parsed)

    # 4) bare time only → assume today or tomorrow
    tm = _TIME_ONLY.search(t)
    if tm:
        hour = int(tm.group("h"))
        minute = int(tm.group("m") or 0)
        ap = (tm.group("ap") or "").lower()
        if not ap:
            ap = "pm" if 1 <= hour <= 7 else "am"
        hour = hour % 12 + (12 if ap == "pm" else 0)
        dt = now.replace(hour=hour, minute=minute)
        dt = _round_to_quarter(dt)
        if dt < now:
            dt += timedelta(days=1)
        return dt

    return None


# —— Duckling fallback —————————————————————————————————————————————


def _parse_duckling(text: str) -> datetime | None:
    """
    Send `text` to local Duckling server and return the first datetime.
    """
    try:
        resp = requests.post(
            "http://localhost:8000/parse",
            json={
                "text": text,
                "locale": "en_US",
                "tz": "UTC",
                "reftime": datetime.now().isoformat(),
            },
            timeout=2.0,
        )
        resp.raise_for_status()
        data = resp.json()
        for ent in data:
            if ent.get("dim") in ("time", "datetime"):
                iso = ent["value"]["value"]
                # handle 'Z' suffix
                if iso.endswith("Z"):
                    iso = iso[:-1] + "+00:00"
                dt = datetime.fromisoformat(iso)
                return _round_to_quarter(dt)
    except Exception:
        return None
    return None


# —— public API ———————————————————————————————————————————————————


def parse_slot(text: str) -> str | None:
    """
    Try to parse 'text' into 'Weekday H:MM AM/PM'.
    1) compact regex + dateparser
    2) Duckling
    3) return None if still no parse
    """
    # 1️⃣ custom
    dt = _parse_custom(text)
    # 2️⃣ duckling fallback
    if dt is None:
        dt = _parse_duckling(text)

    if dt is None:
        return None

    weekday = dt.strftime("%A")
    time_str = dt.strftime("%I:%M %p").lstrip("0")
    return f"{weekday} {time_str}"
