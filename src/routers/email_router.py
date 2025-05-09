from fastapi import APIRouter, Request
import re
from src.handlers.booking_handler import load_bookings, save_all_bookings
from tools.whatsapp_snd_tool import SendWhatsappMsg

router = APIRouter()


@router.post("/incoming/email")
async def handle_email(request: Request):
    payload = await request.json()
    user_message = payload.get("message", "").strip()
    user_number = payload.get("number", "")
    bookings = load_bookings()

    # skip
    if "skip" in user_message.lower():
        bookings[user_number]["awaiting_email"] = False
        save_all_bookings(bookings)
        SendWhatsappMsg.invoke(
            {
                "number": user_number,
                "message": "👍 No problem – WhatsApp reminders only.",
            }
        )
        return {"status": "email_skipped"}

    # naive email regex
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", user_message):
        bookings[user_number]["email"] = user_message
        bookings[user_number]["awaiting_email"] = False
        save_all_bookings(bookings)
        SendWhatsappMsg.invoke(
            {"number": user_number, "message": "✅ Great! I’ll email reminders too."}
        )
        return {"status": "email_saved"}

    # otherwise ask again
    SendWhatsappMsg.invoke(
        {
            "number": user_number,
            "message": "⚠️ That doesn’t look like an email. Send a valid address or say 'skip'.",
        }
    )
    return {"status": "email_retry"}
