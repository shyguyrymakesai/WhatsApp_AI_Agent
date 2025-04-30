# src/routers/email_router.py
import re
from fastapi import Request
from tools.whatsapp_snd_tool import SendWhatsappMsg
from handlers.booking_handler import load_bookings, save_all_bookings


async def handle_email(body: dict) -> dict:
    """
    body == { "user_number": str, "user_message": str }
    """
    user = body["user_number"]
    msg = body["user_message"].strip()
    bookings = load_bookings()

    if bookings.get(user, {}).get("awaiting_email"):
        if "skip" in msg.lower():
            bookings[user]["awaiting_email"] = False
            save_all_bookings(bookings)
            SendWhatsappMsg.invoke(
                {"number": user, "message": "👍 No problem – WhatsApp reminders only."}
            )
            return {"status": "email skipped"}

        # very basic regex
        if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", msg):
            bookings[user]["email"] = msg
            bookings[user]["awaiting_email"] = False
            save_all_bookings(bookings)
            SendWhatsappMsg.invoke(
                {"number": user, "message": "✅ Great! I’ll email reminders too."}
            )
            return {"status": "email saved"}

        SendWhatsappMsg.invoke(
            {
                "number": user,
                "message": "⚠️ That doesn’t look like an email. Send a valid address or say 'skip'.",
            }
        )
        return {"status": "awaiting valid email"}

    return {"status": "not awaiting email"}
