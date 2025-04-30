def pick_slot_from_reply(user_reply: str, shown_slots: list[str]) -> str | None:
    """Return the chosen slot string or None if reply wasn’t a valid index."""
    import re

    m = re.search(r"\b(\d+)\b", user_reply)
    if not m:
        return None
    idx = int(m.group(1)) - 1
    return shown_slots[idx] if 0 <= idx < len(shown_slots) else None
